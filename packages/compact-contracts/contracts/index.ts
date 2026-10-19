import { CompiledContract } from '@midnight-ntwrk/midnight-js-protocol/compact-js';
import { fileURLToPath } from 'node:url';
import { Contract } from './managed/private-amount/contract/index.js';

export { Contract, ledger } from './managed/private-amount/contract/index.js';
export const zkConfigPath = fileURLToPath(new URL('./managed/private-amount', import.meta.url));
export const compiledAmountProbe = CompiledContract.make('TeaPassAmountProbe', Contract).pipe(
  CompiledContract.withWitnesses({}),
  CompiledContract.withCompiledFileAssets(zkConfigPath),
);
