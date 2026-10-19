// Local harness adapted from the Apache-2.0 Midnight hello-world starter.
// TeaPass: private amount probe, adversarial checks, public-only receipt export.
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { randomBytes } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { WebSocket } from 'ws';
import pino from 'pino';
import { filter, firstValueFrom, take, timeout } from 'rxjs';
import { setNetworkId } from '@midnight-ntwrk/midnight-js-network-id';
import { deployContract, submitCallTx } from '@midnight-ntwrk/midnight-js-contracts';
import type { FinalizedTxData } from '@midnight-ntwrk/midnight-js-types';
import { compiledAmountProbe, ledger, zkConfigPath } from '../../contracts/index.js';
import { MidnightWalletProvider, syncWallet } from '../local-wallet.js';
import { buildLocalProviders, localConfig } from '../local-providers.js';

// Required by the indexer's GraphQL subscription transport in Node.
Object.defineProperty(globalThis, 'WebSocket', { value: WebSocket, configurable: true });
const logger = pino({ level: 'info' });
const stateId = 'TeaPassSyntheticAmountProbe';
const receipts: Record<string, unknown>[] = [];
const checks: string[] = [];
const receiptPath = fileURLToPath(new URL('../../../../artifacts/midnight/amount-probe-local.json',
                                        import.meta.url));

function publicReceipt(label: string, data: FinalizedTxData) {
  // Never serialize full SDK return objects: their private fields include witnesses/keys.
  return { label, txId: data.txId, txHash: data.txHash, blockHash: data.blockHash,
           blockHeight: data.blockHeight, status: data.status, protocolVersion: data.protocolVersion };
}

describe.sequential('Private amount proof on the actual local Midnight devnet', () => {
  let wallet: MidnightWalletProvider;
  let providers: ReturnType<typeof buildLocalProviders<'recordAmount'>>;
  let address: string;
  const nonce = randomBytes(32), salt = randomBytes(32);

  beforeAll(async () => {
    if (process.env.MIDNIGHT_NETWORK && process.env.MIDNIGHT_NETWORK !== 'local') {
      throw new Error('Synthetic wallet is local-only');
    }
    setNetworkId(localConfig.networkId);
    wallet = await MidnightWalletProvider.build(logger, localConfig, {
      kind: 'seed', value: '0'.repeat(63) + '1', // Public devnet genesis wallet, never real funds.
    });
    await wallet.start();
    await syncWallet(logger, wallet.wallet, 180_000);
    await firstValueFrom(wallet.wallet.state().pipe(
      filter(state => state.dust.availableCoins.length > 0 && state.dust.balance(new Date()) > 0n),
      take(1), timeout({ first: 180_000 }),
    ));
    providers = buildLocalProviders(wallet, zkConfigPath);
  });

  afterAll(async () => {
    if (wallet) await wallet.stop();
    if (receipts.length) {
      mkdirSync(fileURLToPath(new URL('.', `file://${receiptPath}`)), { recursive: true });
      writeFileSync(receiptPath, JSON.stringify({
        evidenceClass: 'LOCAL_DEVNET', synthetic: true, networkId: 'undeployed',
        recordedAt: new Date().toISOString(), contractAddress: address,
        receipts, checks, complete: checks.length === 4,
        limitations: ['Compatibility probe only; no issuer authority or inventory conservation.',
                      'Rejected calls are local compiled-circuit failures before submission.'],
      }, null, 2) + '\n');
    }
  });

  const call = (amount: bigint, n = nonce, s = salt) => submitCallTx(providers, {
    compiledContract: compiledAmountProbe, contractAddress: address,
    privateStateId: stateId, circuitId: 'recordAmount', args: [amount, n, s],
  });

  async function readLedger() {
    const state = await providers.publicDataProvider.queryContractState(address);
    expect(state).not.toBeNull();
    return ledger(state!.data);
  }

  it('deploys a contract with a finalized indexed receipt', async () => {
    const deployed = await deployContract(providers, {
      compiledContract: compiledAmountProbe, privateStateId: stateId,
      initialPrivateState: {}, args: [1_000_000n],
    });
    address = deployed.deployTxData.public.contractAddress;
    receipts.push(publicReceipt('deployment', deployed.deployTxData.public));
    expect((await readLedger()).maximumGrams).toBe(1_000_000n);
    checks.push('deployment_indexed');
  });

  it('rejects an out-of-range private amount', async () => {
    await expect(call(1_000_001n)).rejects.toThrow('Quantity exceeds maximum');
    expect((await readLedger()).commitments.size()).toBe(0n);
    checks.push('out_of_range_rejected_before_submission');
  });

  it('proves and finalizes a private amount commitment', async () => {
    const result = await call(100_000n);
    receipts.push(publicReceipt('recordAmount', result.public));
    const state = await readLedger();
    expect(state.commitments.size()).toBe(1n);
    expect(state.usedTags.size()).toBe(1n);
    expect(Object.keys(state).sort()).toEqual(['commitments', 'maximumGrams', 'usedTags']);
    checks.push('private_amount_proven_and_indexed');
  });

  it('rejects replay and preserves the indexed commitment count', async () => {
    await expect(call(200_000n, nonce, randomBytes(32))).rejects.toThrow('Nonce already used');
    expect((await readLedger()).commitments.size()).toBe(1n);
    checks.push('replay_rejected_before_submission');
  });
});
