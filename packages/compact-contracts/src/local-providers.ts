// Adapted from midnightntwrk/example-hello-world (Apache-2.0).
// TeaPass changes: local-only configuration, random ephemeral storage password,
// separate ignored database directory and typed contract providers.
import { randomBytes } from 'node:crypto';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { indexerPublicDataProvider } from '@midnight-ntwrk/midnight-js-indexer-public-data-provider';
import { httpClientProofProvider } from '@midnight-ntwrk/midnight-js-http-client-proof-provider';
import { NodeZkConfigProvider } from '@midnight-ntwrk/midnight-js-node-zk-config-provider';
import { levelPrivateStateProvider } from '@midnight-ntwrk/midnight-js-level-private-state-provider';
import type { MidnightProviders } from '@midnight-ntwrk/midnight-js-types';
import type { MidnightWalletProvider } from './local-wallet.js';

export const localConfig = Object.freeze({
  networkId: 'undeployed',
  walletNetworkId: 'undeployed',
  indexer: 'http://127.0.0.1:8088/api/v4/graphql',
  indexerWS: 'ws://127.0.0.1:8088/api/v4/graphql/ws',
  node: 'http://127.0.0.1:9944',
  nodeWS: 'ws://127.0.0.1:9944',
  proofServer: 'http://127.0.0.1:6300',
  faucet: '',
});

export function buildLocalProviders<C extends string = 'recordAmount', P = Record<string, never>>(wallet: MidnightWalletProvider, zkConfigPath: string) {
  if (process.env.MIDNIGHT_NETWORK && process.env.MIDNIGHT_NETWORK !== 'local') {
    throw new Error('This harness is restricted to the synthetic local devnet');
  }
  const password = `TeaPass!${randomBytes(32).toString('base64url')}`;
  const directory = fileURLToPath(new URL('../.private-state/', import.meta.url));
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  const zkConfigProvider = new NodeZkConfigProvider<C>(zkConfigPath);
  return {
    privateStateProvider: levelPrivateStateProvider<string, P>({
      midnightDbName: `${directory}/probe-${randomBytes(12).toString('hex')}`,
      privateStoragePasswordProvider: () => password,
      accountId: wallet.getCoinPublicKey(),
    }),
    publicDataProvider: indexerPublicDataProvider(localConfig.indexer, localConfig.indexerWS),
    zkConfigProvider,
    proofProvider: httpClientProofProvider(localConfig.proofServer, zkConfigProvider),
    walletProvider: wallet,
    midnightProvider: wallet,
  } satisfies MidnightProviders<C, string, P>;
}
