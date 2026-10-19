import { readFileSync,writeFileSync } from 'node:fs';
import { WebSocket } from 'ws';
import { indexerPublicDataProvider } from '@midnight-ntwrk/midnight-js-indexer-public-data-provider';
import { ledger } from '../contracts/inventory.js';
import { verifyClaim } from './claim-verifier.js';
import { localConfig } from './local-providers.js';
Object.defineProperty(globalThis,'WebSocket',{value:WebSocket,configurable:true});
const artifact=JSON.parse(readFileSync('../../artifacts/midnight/inventory-local.json','utf8'));
const provider=indexerPublicDataProvider(localConfig.indexer,localConfig.indexerWS);
const state=await provider.queryContractState(artifact.contractAddress);
if(!state) throw Error('Missing deployed contract');
const claims=[];
for(const [id] of ledger(state.data).complianceClaims) {
  claims.push(await verifyClaim({contractAddress:artifact.contractAddress,network:localConfig.networkId,
    indexer:localConfig.indexer,indexerWS:localConfig.indexerWS,node:localConfig.node},Buffer.from(id).toString('hex')));
}
if(claims.length!==1 || claims[0]?.status!=='INVALID' || !claims[0].reasons.includes('LAB_REVOKED'))
  throw Error('Expected the real revoked laboratory claim to remain invalid');
writeFileSync('../../artifacts/midnight/public-claims-local.json',JSON.stringify({evidenceClass:'LOCAL_DEVNET',synthetic:true,claims},null,2)+'\n');
console.log('Pinned verifier keys and finalized state checked; revoked lab claim is INVALID.');
process.exit(0);
