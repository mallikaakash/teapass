import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { randomBytes, randomUUID, createHash } from 'node:crypto';
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { WebSocket } from 'ws';
import pino from 'pino';
import { filter, firstValueFrom, take, timeout } from 'rxjs';
import { setNetworkId } from '@midnight-ntwrk/midnight-js-network-id';
import { deployContract, submitCallTx } from '@midnight-ntwrk/midnight-js-contracts';
import type { FinalizedTxData } from '@midnight-ntwrk/midnight-js-types';
import { compiledInventory, ledger, pureCircuits, zkConfigPath,
  type InventoryCircuit, type InventoryPrivateState, type Note, Contract } from '../../contracts/inventory.js';
import { MidnightWalletProvider, syncWallet } from '../local-wallet.js';
import { buildLocalProviders, localConfig } from '../local-providers.js';

Object.defineProperty(globalThis, 'WebSocket', { value: WebSocket, configurable: true });
const bytes = () => randomBytes(32);
const key = pureCircuits.authorityKey;
const logger = pino({ level: 'warn' });
const admin=bytes(), issuer=bytes(), owner=bytes(), lab=bytes();
const origin=bytes(), network=bytes();
const outputBatchId=randomUUID();
const outputBatchReference=createHash('sha256').update('TEAPASS_BATCH_V1\0teapass-local\0'+outputBatchId).digest();
const receipts: Record<string, unknown>[] = [], checks: string[] = [];
const stateIds = new Map<Uint8Array,string>([[admin,'admin'],[issuer,'issuer'],[owner,'owner'],[lab,'lab']]);
const a: Note={version:1n,owner:key(owner),issuer:key(issuer),batch:bytes(),material:2n,
  quantity:100_000n,originClass:origin,nonce:bytes()};
const b: Note={...a,batch:bytes(),quantity:80_000n,nonce:bytes()};
const outputs: [Note,Note,Note]=[
  {...a,quantity:40_000n,nonce:bytes()}, {...b,quantity:40_000n,nonce:bytes()},
  {...a,batch:outputBatchReference,material:3n,issuer:key(owner),quantity:100_000n,nonce:bytes()},
];
const salts: [Uint8Array,Uint8Array]=[bytes(),bytes()];
const outputSalts: [Uint8Array,Uint8Array,Uint8Array]=[bytes(),bytes(),bytes()];

// Negative cases execute the generated circuit against freshly indexed chain state;
// they fail before proving/submission. Positive cases produce real settled receipts.
describe.sequential('TeaPass inventory on local Midnight', () => {
  let wallet: MidnightWalletProvider;
  let providers: ReturnType<typeof buildLocalProviders<InventoryCircuit,InventoryPrivateState>>;
  let address: string;
  async function call<C extends InventoryCircuit>(who: Uint8Array, circuitId: C,
    args: Parameters<Contract<InventoryPrivateState>['impureCircuits'][C]> extends [unknown,...infer A] ? A : never) {
    const start=performance.now();
    const result = await submitCallTx(providers, { compiledContract:compiledInventory,
      contractAddress:address,privateStateId:stateIds.get(who)!,circuitId,args } as never);
    record(circuitId,result.public,performance.now()-start);
    return result;
  }
  function record(label: string, d: FinalizedTxData, elapsedMs: number) {
    receipts.push({label,txId:d.txId,txHash:d.txHash,blockHash:d.blockHash,
      blockHeight:d.blockHeight,status:d.status,protocolVersion:d.protocolVersion,elapsedMs});
  }
  async function view() {
    const state=await providers.publicDataProvider.queryContractState(address);
    if(!state) throw new Error('Indexed state missing');
    return ledger(state.data);
  }
  beforeAll(async () => {
    setNetworkId(localConfig.networkId);
    wallet=await MidnightWalletProvider.build(logger,localConfig,{kind:'seed',value:'0'.repeat(63)+'1'});
    await wallet.start(); await syncWallet(logger,wallet.wallet,180_000);
    await firstValueFrom(wallet.wallet.state().pipe(filter(s=>s.dust.availableCoins.length>0 &&
      s.dust.balance(new Date())>0n),take(1),timeout({first:180_000})));
    providers=buildLocalProviders<InventoryCircuit,InventoryPrivateState>(wallet,zkConfigPath);
  });
  afterAll(async () => {
    if(wallet) await wallet.stop();
    if(receipts.length) {
      const path=resolve('../../artifacts/midnight/inventory-local.json'); mkdirSync(dirname(path),{recursive:true});
      writeFileSync(path,JSON.stringify({evidenceClass:'LOCAL_DEVNET',synthetic:true,networkId:'undeployed',
        recordedAt:new Date().toISOString(),contractAddress:address,
        sourceSha256:createHash('sha256').update(readFileSync('contracts/inventory.compact')).digest('hex'),
        checks,receipts,complete:checks.length===6,
        publicBinding:{deploymentId:'teapass-local',batchId:outputBatchId,batchReference:outputBatchReference.toString('hex')},
        limitations:['Synthetic local network; no public deployment or real institutions.',
          'Negative calls rejected before submission; timings combine proof and settlement.',
          'Public commitment lookups reveal links; private amounts and secrets omitted.']},null,2)+'\n');
    }
  });
  it('deploys governed inventory',async()=>{
    const start=performance.now();
    const d=await deployContract(providers,{compiledContract:compiledInventory,privateStateId:'admin',
      initialPrivateState:{secret:admin},args:[network,key(admin)]});
    address=d.deployTxData.public.contractAddress;record('deployment',d.deployTxData.public,performance.now()-start);
    for(const [secret,id] of stateIds) await providers.privateStateProvider.set(id,{secret});
    expect((await view()).notes.size()).toBe(0n); checks.push('deployment_indexed');
  });
  it('rejects forged issuance and issues two authorized notes',async()=>{
    await expect(call(owner,'issue',[a,salts[0],bytes()])).rejects.toThrow('Unknown issuer');
    await call(admin,'setIssuer',[key(issuer),2n,true]);
    await call(issuer,'issue',[a,salts[0],bytes()]); await call(issuer,'issue',[b,salts[1],bytes()]);
    expect((await view()).notes.size()).toBe(2n);checks.push('authorized_issuance_indexed');
  });
  it('rejects inflation and proves an atomic 100+80 to 40+40+100 blend',async()=>{
    await expect(call(owner,'blend',[[a,b],salts,[outputs[0],outputs[1],{...outputs[2],quantity:100_001n}],outputSalts]))
      .rejects.toThrow('Blend mass imbalance');
    await call(owner,'blend',[[a,b],salts,outputs,outputSalts]);
    expect((await view()).notes.size()).toBe(5n);expect((await view()).spentNullifiers.size()).toBe(2n);
    checks.push('conserved_blend_indexed');
  });
  it('rejects a repeated spend using current chain state',async()=>{
    await expect(call(owner,'blend',[[a,b],salts,outputs,outputSalts])).rejects.toThrow('Note already consumed');
    expect((await view()).notes.size()).toBe(5n);checks.push('double_spend_rejected_before_submission');
  });
  it('anchors a lab attestation and proves the explicit demo threshold',async()=>{
    await call(admin,'setLab',[key(lab),true]);
    const policy=bytes(), now=BigInt(Math.floor(Date.now()/1000));
    await call(admin,'registerPolicy',[policy,{analyte:bytes(),method:bytes(),unit:1n,threshold:5n,
      maxAgeSeconds:3600n,validFrom:now-86400n,validUntil:now+86400n}]);
    // Compute commitment locally from the real indexed state without publishing a witness call.
    const {createCircuitContext}=await import('@midnight-ntwrk/compact-runtime');
    const {Contract}=await import('../../contracts/inventory.js');
    const state=await providers.publicDataProvider.queryContractState(address);
    const contract=new Contract<InventoryPrivateState>({actorSecret:({privateState})=>[privateState,privateState.secret]});
    const ctx=createCircuitContext(address,wallet.getCoinPublicKey(),state!.data,{secret:owner});
    const batchCommitment=contract.impureCircuits.noteCommitment(ctx,outputs[2],outputSalts[2]).result;
    const record={batchCommitment,lab:key(lab),policy,measurement:3n,sampleTime:now-60n,expiresAt:now+1800n,nonce:bytes()};
    const salt=bytes();await call(lab,'anchorLab',[record,salt]);
    await expect(call(owner,'proveCompliance',[{...record,batchCommitment:bytes()},salt]))
      .rejects.toThrow('Unauthenticated lab record');
    await call(owner,'proveCompliance',[record,salt]);
    expect((await view()).complianceClaims.size()).toBe(1n);checks.push('authenticated_compliance_indexed');
  });
  it('records current revocation independently of historical proof validity',async()=>{
    await call(admin,'setLab',[key(lab),false]);
    expect((await view()).approvedLabs.member(key(lab))).toBe(false);
    expect((await view()).complianceClaims.size()).toBe(1n);checks.push('lab_revocation_indexed');
  });
});
