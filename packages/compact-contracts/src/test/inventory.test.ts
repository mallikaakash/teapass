import { describe, expect, it } from 'vitest';
import { randomBytes } from 'node:crypto';
import {
  createCircuitContext, createConstructorContext, StateValue,
  type CircuitContext, type CircuitResults,
} from '@midnight-ntwrk/compact-runtime';
import { Contract, ledger, pureCircuits, type Note, type LabRecord, type Policy }
  from '../../contracts/managed/inventory/contract/index.js';

type PrivateState = { secret: Uint8Array };
const bytes = () => randomBytes(32);
const key = pureCircuits.authorityKey;
const coin = '00'.repeat(32);

class Harness {
  admin = bytes();
  issuer = bytes();
  owner = bytes();
  lab = bytes();
  now = 1_790_000_000;
  address = 'aa'.repeat(32);
  contract = new Contract<PrivateState>({
    actorSecret: ({ privateState }) => [privateState, privateState.secret],
  });
  state: StateValue;
  constructor() {
    this.state = this.contract.initialState(
      createConstructorContext({ secret: this.admin }, coin), bytes(), key(this.admin),
    ).currentContractState.data.state;
  }
  run(name: keyof Contract<PrivateState>['impureCircuits'], secret: Uint8Array, ...args: unknown[]) {
    // Model transaction boundaries explicitly: a failing execution never replaces committed state.
    const context = createCircuitContext(this.address, coin, StateValue.decode(this.state.encode()),
      { secret }, undefined, undefined, this.now);
    const circuit = this.contract.impureCircuits[name] as unknown as
      (context: CircuitContext<PrivateState>, ...args: unknown[]) => CircuitResults<PrivateState, unknown>;
    const result = circuit(context, ...args);
    this.state = result.context.currentQueryContext.state.state;
    return result.result;
  }
  view() { return ledger(this.state); }
  approve(material = 2n) { this.run('setIssuer', this.admin, key(this.issuer), material, true); }
  note(quantity = 100_000n, changes: Partial<Note> = {}): Note {
    return { version: 1n, owner: key(this.owner), issuer: key(this.issuer), batch: bytes(),
      material: 2n, quantity, originClass: new Uint8Array(32).fill(7), nonce: bytes(), ...changes };
  }
  issue(note = this.note(), salt = bytes(), nonce = bytes()) {
    this.run('issue', this.issuer, note, salt, nonce);
    return { note, salt, nonce };
  }
  funded() { this.approve(); return [this.issue(), this.issue(this.note(80_000n))] as const; }
  blendOutputs(a: Note, b: Note): Note[] {
    return [this.note(40_000n, { ...a, quantity: 40_000n, nonce: bytes() }),
      this.note(40_000n, { ...b, quantity: 40_000n, nonce: bytes() }),
      this.note(100_000n, { material: 3n, issuer: key(this.owner) })];
  }
  labSetup(measurement = 3n, recordChanges: Partial<LabRecord> = {}) {
    this.approve();
    const { note, salt } = this.issue();
    const batch = this.run('noteCommitment', this.owner, note, salt) as Uint8Array;
    this.run('setLab', this.admin, key(this.lab), true);
    const policyId = bytes();
    const policy: Policy = { analyte: bytes(), method: bytes(), unit: 1n, threshold: 5n,
      maxAgeSeconds: 3600n, validFrom: BigInt(this.now - 86400), validUntil: BigInt(this.now + 86400) };
    this.run('registerPolicy', this.admin, policyId, policy);
    const record: LabRecord = { batchCommitment: batch, lab: key(this.lab), policy: policyId,
      measurement, sampleTime: BigInt(this.now - 60), expiresAt: BigInt(this.now + 1800),
      nonce: bytes(), ...recordChanges };
    const labSalt = bytes();
    this.run('anchorLab', this.lab, record, labSalt);
    return { record, labSalt, policyId };
  }
}

describe('TeaPass compiled inventory rules (runtime execution)', () => {
  it('requires cryptographic governance and issuer authority', () => {
    const h = new Harness();
    expect(() => h.run('setIssuer', h.owner, key(h.owner), 2n, true)).toThrow('Unauthorized governance');
    expect(() => h.issue()).toThrow('Unknown issuer');
    h.approve();
    h.issue();
    expect(h.view().notes.size()).toBe(1n);
    expect(() => h.run('issue', h.owner, h.note(), bytes(), bytes())).toThrow('Unknown issuer');
  });
  it('rejects revoked issuers, mismatched identities and wrong material', () => {
    const h = new Harness(); h.approve();
    expect(() => h.issue(h.note(10n, { issuer: bytes() }))).toThrow('Issuer binding mismatch');
    expect(() => h.issue(h.note(10n, { material: 1n }))).toThrow('Issuer material not allowed');
    h.run('setIssuer', h.admin, key(h.issuer), 2n, false);
    expect(() => h.issue()).toThrow('Revoked issuer');
  });
  it('rejects duplicate issuance nonce and duplicate commitment independently', () => {
    const h = new Harness(); h.approve(); const a = h.issue();
    expect(() => h.issue(h.note(), bytes(), a.nonce)).toThrow('Issuance replay');
    expect(() => h.issue(a.note, a.salt)).toThrow('Duplicate note commitment');
    expect(h.view().notes.size()).toBe(1n);
  });
  it.each([0n, -1n, 1_000_000_000_001n, 1n << 64n])('rejects invalid quantity %s', q => {
    const h = new Harness(); h.approve(); expect(() => h.issue(h.note(q))).toThrow();
  });
  it('enforces the exact 100+80 -> 40+40+100 blend and rejects a second spend', () => {
    const h = new Harness(); const [a,b] = h.funded();
    const outputs = h.blendOutputs(a.note,b.note), salts = [bytes(),bytes(),bytes()];
    h.run('blend', h.owner, [a.note,b.note], [a.salt,b.salt], outputs, salts);
    expect(h.view().notes.size()).toBe(5n);
    expect(h.view().spentNullifiers.size()).toBe(2n);
    expect(() => h.run('blend', h.owner, [a.note,b.note], [a.salt,b.salt], outputs, salts))
      .toThrow('Note already consumed');
  });
  it('rejects duplicated inputs atomically', () => {
    const h = new Harness(); const [a] = h.funded();
    const outputs = h.blendOutputs(a.note,a.note); outputs[2].quantity = 120_000n;
    expect(() => h.run('blend', h.owner, [a.note,a.note], [a.salt,a.salt], outputs,
      [bytes(),bytes(),bytes()])).toThrow('Note already consumed');
    expect(h.view().spentNullifiers.size()).toBe(0n);
    expect(h.view().notes.size()).toBe(2n);
  });
  it('rejects inflation without consuming any note', () => {
    const h = new Harness(); const [a,b] = h.funded();
    const outputs = h.blendOutputs(a.note,b.note); outputs[2].quantity++;
    expect(() => h.run('blend', h.owner, [a.note,b.note], [a.salt,b.salt], outputs,
      [bytes(),bytes(),bytes()])).toThrow('Blend mass imbalance');
    expect(h.view().spentNullifiers.size()).toBe(0n);
  });
  it('rejects wrong ownership, altered note content and wrong salt', () => {
    const h = new Harness(); h.approve(); const a=h.issue();
    const output={...a.note,nonce:bytes()};
    expect(() => h.run('transfer', bytes(), a.note,a.salt,output,bytes())).toThrow('Wrong note owner');
    expect(() => h.run('transfer', h.owner,a.note,bytes(),output,bytes())).toThrow('Unknown note commitment');
    const forged={...a.note,quantity:1n};
    expect(() => h.run('transfer',h.owner,forged,a.salt,{...output,quantity:1n},bytes()))
      .toThrow('Unknown note commitment');
  });
  it('transfers ownership with consume-and-create and permits only the recipient to spend', () => {
    const h=new Harness(); h.approve(); const a=h.issue(); const receiver=bytes();
    const output={...a.note,owner:key(receiver),nonce:bytes()}, salt=bytes();
    h.run('transfer',h.owner,a.note,a.salt,output,salt);
    const next={...output,nonce:bytes()};
    expect(() => h.run('transfer',h.owner,output,salt,next,bytes())).toThrow('Wrong note owner');
    h.run('transfer',receiver,output,salt,next,bytes());
    expect(h.view().spentNullifiers.size()).toBe(2n);
  });
  it('splits exact amounts and rejects changed origin or duplicate outputs', () => {
    const h=new Harness(); h.approve(); const a=h.issue();
    const outputs=[{...a.note,quantity:50_000n,nonce:bytes()},
                   {...a.note,quantity:50_000n,nonce:bytes()}];
    expect(() => h.run('split',h.owner,a.note,a.salt,
      [{...outputs[0],originClass:bytes()},outputs[1]],[bytes(),bytes()])).toThrow('Origin class mismatch');
    const duplicateSalt=bytes();
    expect(() => h.run('split',h.owner,a.note,a.salt,[outputs[0],outputs[0]],
      [duplicateSalt,duplicateSalt])).toThrow('Duplicate note commitment');
    expect(h.view().spentNullifiers.size()).toBe(0n);
    h.run('split',h.owner,a.note,a.salt,outputs,[bytes(),bytes()]);
    expect(h.view().notes.size()).toBe(3n);
  });
  it('enforces processing mass balance and the explicit demo yield policy', () => {
    const h=new Harness(); h.approve(1n); const a=h.issue(h.note(100_000n,{material:1n}));
    const output={...a.note,material:2n,quantity:25_000n,nonce:bytes()};
    expect(() => h.run('process',h.owner,a.note,a.salt,output,bytes(),10_000n,60_000n))
      .toThrow('Processing mass imbalance');
    expect(() => h.run('process',h.owner,a.note,a.salt,{...output,quantity:90_000n},bytes(),0n,10_000n))
      .toThrow('Yield above demo policy');
    h.run('process',h.owner,a.note,a.salt,output,bytes(),10_000n,65_000n);
    expect(h.view().spentNullifiers.size()).toBe(1n);
  });
  it('requires matching provenance classes when blending', () => {
    const h=new Harness(); h.approve();const a=h.issue(),b=h.issue(h.note(80_000n,{originClass:bytes()}));
    expect(() => h.run('blend',h.owner,[a.note,b.note],[a.salt,b.salt],
      h.blendOutputs(a.note,b.note),[bytes(),bytes(),bytes()])).toThrow('Mixed origin classes');
  });
});

describe('Authenticated laboratory and policy predicates', () => {
  it('proves a bounded measurement bound to an authenticated batch', () => {
    const h=new Harness();const {record,labSalt}=h.labSetup();
    h.run('proveCompliance',h.owner,record,labSalt);
    expect(h.view().complianceClaims.size()).toBe(1n);
    const claim=[...h.view().complianceClaims][0][1];
    expect(Object.keys(claim).sort()).toEqual(['batchCommitment','expiresAt','lab','policy']);
  });
  it('rejects unauthenticated, altered and wrong-batch evidence', () => {
    const h=new Harness();const {record,labSalt}=h.labSetup();
    for(const changed of [{...record,measurement:0n},{...record,batchCommitment:bytes()}]) {
      expect(() => h.run('proveCompliance',h.owner,changed,labSalt)).toThrow('Unauthenticated lab record');
    }
    expect(() => h.run('anchorLab',h.owner,record,bytes())).toThrow('Unapproved laboratory');
  });
  it('rejects a measurement above the specified threshold', () => {
    const h=new Harness();const {record,labSalt}=h.labSetup(6n);
    expect(() => h.run('proveCompliance',h.owner,record,labSalt)).toThrow('Measurement exceeds threshold');
  });
  it('rejects revoked lab credentials and revoked policies', () => {
    const h=new Harness();const {record,labSalt,policyId}=h.labSetup();
    h.run('setLab',h.admin,key(h.lab),false);
    expect(() => h.run('proveCompliance',h.owner,record,labSalt)).toThrow('Revoked laboratory');
    h.run('setLab',h.admin,key(h.lab),true);h.run('revokePolicy',h.admin,policyId);
    expect(() => h.run('proveCompliance',h.owner,record,labSalt)).toThrow('Revoked policy');
  });
  it.each(['expired','future','old'])('rejects %s certificates', kind => {
    const h=new Harness();
    const changes=kind==='expired'?{sampleTime:BigInt(h.now-120),expiresAt:BigInt(h.now-1)}:
      kind==='future'?{sampleTime:BigInt(h.now+1)}:{sampleTime:BigInt(h.now-7200)};
    const {record,labSalt}=h.labSetup(3n,changes);
    expect(() => h.run('proveCompliance',h.owner,record,labSalt)).toThrow();
  });
});

describe('Current public verification and spend identity', () => {
  it('allows independently committed notes to use the same private nonce without sharing spend state', () => {
    const h=new Harness();h.approve();const a=h.issue();
    const b=h.issue({...a.note,batch:bytes()},bytes());
    h.run('transfer',h.owner,a.note,a.salt,{...a.note,nonce:bytes()},bytes());
    h.run('transfer',h.owner,b.note,b.salt,{...b.note,nonce:bytes()},bytes());
    expect(h.view().spentNullifiers.size()).toBe(2n);
  });
  it('expires claims at sample age, and reports current lab/policy revocations', async () => {
    const {publicClaim}=await import('../claim-verifier.js');
    const h=new Harness();const {record,labSalt,policyId}=h.labSetup(3n,{expiresAt:BigInt(h.now+7200)});
    h.run('proveCompliance',h.owner,record,labSalt);
    const [id,claim]=[...h.view().complianceClaims][0];const hex=Buffer.from(id).toString('hex');
    expect(claim.expiresAt).toBe(BigInt(h.now+3540));
    expect(publicClaim(h.view(),hex,BigInt(h.now))?.status).toBe('VALID');
    expect(publicClaim(h.view(),hex,BigInt(h.now+3600))?.reasons).toContain('EXPIRED');
    h.run('setLab',h.admin,key(h.lab),false);
    expect(publicClaim(h.view(),hex,BigInt(h.now))?.reasons).toContain('LAB_REVOKED');
    h.run('revokePolicy',h.admin,policyId);
    expect(publicClaim(h.view(),hex,BigInt(h.now))?.reasons).toContain('POLICY_REVOKED');
    expect(publicClaim(h.view(),Buffer.from(bytes()).toString('hex'),BigInt(h.now))).toBeNull();
  });
});
