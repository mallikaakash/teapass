import { describe, it, expect } from 'vitest';
import { randomBytes } from 'node:crypto';
import { createCircuitContext, createConstructorContext } from '@midnight-ntwrk/compact-runtime';
import { Contract, ledger } from '../../contracts/managed/private-amount/contract/index.js';

const address = 'ab'.repeat(32);
const coin = '00'.repeat(32);

function setup(maximum = 1_000_000n) {
  const contract = new Contract({});
  const initial = contract.initialState(createConstructorContext({}, coin), maximum);
  const context = createCircuitContext(address, coin, initial.currentContractState, {});
  return { contract, context };
}

describe('Compiled Compact private-amount probe (runtime, not a network proof)', () => {
  it('accepts a bounded quantity and stores only commitment/tag fields', () => {
    const { contract, context } = setup();
    const result = contract.circuits.recordAmount(context, 100_000n, randomBytes(32), randomBytes(32));
    const state = ledger(result.context.currentQueryContext.state);
    expect(state.commitments.size()).toBe(1n);
    expect(state.usedTags.size()).toBe(1n);
    expect(Object.keys(state).sort()).toEqual(['commitments', 'maximumGrams', 'usedTags']);
  });

  it.each([0n, -1n, 1_000_001n, 1n << 64n])('rejects invalid quantity %s', (quantity) => {
    const { contract, context } = setup();
    expect(() => contract.circuits.recordAmount(context, quantity, randomBytes(32), randomBytes(32)))
      .toThrow();
  });

  it('rejects a replay even if the caller changes quantity and salt', () => {
    const { contract, context } = setup();
    const nonce = randomBytes(32);
    const first = contract.circuits.recordAmount(context, 100n, nonce, randomBytes(32));
    expect(() => contract.circuits.recordAmount(first.context, 200n, nonce, randomBytes(32)))
      .toThrow('Nonce already used');
  });

  it('fresh salts produce distinct commitments for the same quantity and nonce', () => {
    const nonce = randomBytes(32);
    const a = setup();
    const b = setup();
    const first = a.contract.circuits.recordAmount(a.context, 100n, nonce, randomBytes(32));
    const second = b.contract.circuits.recordAmount(b.context, 100n, nonce, randomBytes(32));
    const ca = [...ledger(first.context.currentQueryContext.state).commitments][0];
    const cb = [...ledger(second.context.currentQueryContext.state).commitments][0];
    expect(ca).not.toEqual(cb);
  });

  it('binds commitments and replay tags to the deployed contract', () => {
    const nonce = randomBytes(32), salt = randomBytes(32);
    const a = setup();
    const b = setup();
    const initial = b.contract.initialState(createConstructorContext({}, coin), 1_000_000n);
    const other = createCircuitContext('cd'.repeat(32), coin, initial.currentContractState, {});
    const ra = a.contract.circuits.recordAmount(a.context, 100n, nonce, salt);
    const rb = b.contract.circuits.recordAmount(other, 100n, nonce, salt);
    expect([...ledger(ra.context.currentQueryContext.state).commitments])
      .not.toEqual([...ledger(rb.context.currentQueryContext.state).commitments]);
    expect([...ledger(ra.context.currentQueryContext.state).usedTags])
      .not.toEqual([...ledger(rb.context.currentQueryContext.state).usedTags]);
  });

  it('rejects an invalid constructor bound', () => {
    expect(() => setup(0n)).toThrow('Maximum must be positive');
  });
});
