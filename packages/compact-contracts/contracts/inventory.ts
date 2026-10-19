import { CompiledContract } from '@midnight-ntwrk/midnight-js-protocol/compact-js';
import { fileURLToPath } from 'node:url';
import { Contract, type Witnesses } from './managed/inventory/contract/index.js';
export { Contract, ledger, pureCircuits } from './managed/inventory/contract/index.js';
export type { Note, LabRecord, Policy } from './managed/inventory/contract/index.js';
export type InventoryPrivateState = { secret: Uint8Array };
export type InventoryCircuit = keyof Contract<InventoryPrivateState>['impureCircuits'];
export const zkConfigPath = fileURLToPath(new URL('./managed/inventory', import.meta.url));
const witnesses: Witnesses<InventoryPrivateState> = {
  actorSecret: ({ privateState }) => [privateState, privateState.secret],
};
export const compiledInventory = CompiledContract.make('TeaPassInventory', Contract).pipe(
  CompiledContract.withWitnesses(witnesses),
  CompiledContract.withCompiledFileAssets(zkConfigPath),
);
