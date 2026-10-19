import { timingSafeEqual } from 'node:crypto';
import { ContractState } from '@midnight-ntwrk/midnight-js-protocol/compact-runtime';
import { NodeZkConfigProvider } from '@midnight-ntwrk/midnight-js-node-zk-config-provider';
import { ledger, zkConfigPath, type InventoryCircuit } from '../contracts/inventory.js';

const hex = (bytes: Uint8Array) => Buffer.from(bytes).toString('hex');
export class VerificationUnavailable extends Error {}
export const bytes32 = (value: string) => {
  if(!/^[a-f0-9]{64}$/.test(value)) throw new TypeError('Expected 32-byte hex');
  return Uint8Array.from(Buffer.from(value,'hex'));
};
export type VerifierConfig = {contractAddress:string; network:string; indexer:string; indexerWS:string; node:string};
export function publicClaim(state: ReturnType<typeof ledger>, claimId: string, nowSeconds: bigint) {
  const id=bytes32(claimId);
  if(!state.complianceClaims.member(id)) return null;
  const claim=state.complianceClaims.lookup(id);
  const policy=state.policies.lookup(claim.policy);
  const metadata=state.noteMetadata.lookup(claim.batchCommitment);
  const reasons=[];
  if(!state.approvedLabs.member(claim.lab)) reasons.push('LAB_REVOKED');
  if(state.revokedPolicies.member(claim.policy)) reasons.push('POLICY_REVOKED');
  if(claim.expiresAt<=nowSeconds || policy.validUntil<=nowSeconds) reasons.push('EXPIRED');
  if(policy.validFrom>nowSeconds) reasons.push('POLICY_NOT_YET_VALID');
  return {claimId,claimType:'LAB_MEASUREMENT_AT_OR_BELOW_POLICY_THRESHOLD',
    status:reasons.length?'INVALID':'VALID',reasons,batchCommitment:hex(claim.batchCommitment),
    batchReference:hex(metadata.batch),materialClass:metadata.material.toString(),
    labAuthority:hex(claim.lab),policyId:hex(claim.policy),expiresAt:claim.expiresAt.toString(),
    policy:{analyte:hex(policy.analyte),method:hex(policy.method),unit:policy.unit.toString(),
      threshold:policy.threshold.toString(),validFrom:policy.validFrom.toString(),validUntil:policy.validUntil.toString()},
    limitations:['Digital claim about the committed tested note; physical sample identity is not guaranteed.',
      'No blanket origin, food-safety or QR anti-counterfeit claim.']};
}

export async function verifyClaim(config: VerifierConfig, claimId: string) {
  bytes32(config.contractAddress);bytes32(claimId);
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),8000);
  try {
    const request=await fetch(config.node,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({jsonrpc:'2.0',id:1,method:'chain_getFinalizedHead',params:[]}),signal:controller.signal});
    if(!request.ok) throw new VerificationUnavailable('Node unavailable');
    const head=await request.json() as {result?: string;error?:unknown};
    if(head.error || !/^0x[a-f0-9]{64}$/.test(head.result??'')) throw new VerificationUnavailable('Invalid finality response');
    const rpc=async(method:string,params:unknown[])=>{
      const response=await fetch(config.node,{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({jsonrpc:'2.0',id:1,method,params}),signal:controller.signal});
      if(!response.ok) throw new VerificationUnavailable('Node unavailable');
      const body=await response.json() as {result:any;error?:unknown};
      if(body.error || body.result==null) throw new VerificationUnavailable('Node response invalid');
      return body.result;
    };
    const finalizedHeader=await rpc('chain_getHeader',[head.result]);
    if(typeof finalizedHeader.number!=='string' || !/^0x[a-f0-9]+$/i.test(finalizedHeader.number))
      throw new VerificationUnavailable('Invalid finalized height');
    const finalizedHeight=parseInt(finalizedHeader.number,16);
    if(!Number.isSafeInteger(finalizedHeight) || finalizedHeight<0) throw new VerificationUnavailable('Invalid finalized height');
    const indexed=await fetch(config.indexer,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({query:`query($address:HexEncoded!){block{height hash}
        contractAction(address:$address){state transaction{block{height hash}}}}`,
        variables:{address:config.contractAddress}}),signal:controller.signal});
    if(!indexed.ok) throw new VerificationUnavailable('Indexer unavailable');
    const snapshot=await indexed.json() as {errors?:unknown;data?:{block:{height:number;hash:string};
      contractAction:{state:string;transaction:{block:{height:number;hash:string}}}|null}};
    const action=snapshot.data?.contractAction;
    // Indexer block offsets select exact actions, not an as-of snapshot. Fetch the latest action
    // and its block atomically, require a caught-up indexer and independently check canonical finality.
    if(snapshot.errors || !action || !Number.isSafeInteger(snapshot.data!.block.height) ||
       !Number.isSafeInteger(action.transaction.block.height) || action.transaction.block.height<0 ||
       snapshot.data!.block.height<finalizedHeight ||
       action.transaction.block.height>finalizedHeight) throw new VerificationUnavailable('Indexer not finalized/caught up');
    const canonical=await rpc('chain_getBlockHash',[action.transaction.block.height]);
    if(typeof canonical!=='string' || !/^0x[a-f0-9]{64}$/.test(canonical) || canonical.slice(2)!==action.transaction.block.hash) throw new VerificationUnavailable('Noncanonical action');
    const current=ContractState.deserialize(Buffer.from(action.state,'hex'));
    // Detect replacement/upgrades: all installed verifier keys must match this exact compiled build.
    const zk=new NodeZkConfigProvider<InventoryCircuit>(zkConfigPath);
    const expected=await zk.getVerifierKeys(['anchorLab','blend','issue','noteCommitment','process','proveCompliance',
      'registerPolicy','revokePolicy','setIssuer','setLab','split','transfer']);
    if(expected.length!==current.operations().length) throw new VerificationUnavailable('Contract build mismatch');
    for(const [name,key] of expected) {
      const actual=current.operation(name)?.verifierKey;
      if(!actual || actual.length!==key.length || !timingSafeEqual(actual,key))
        throw new VerificationUnavailable('Contract verifier mismatch');
    }
    const claim=publicClaim(ledger(current.data),claimId,BigInt(Math.floor(Date.now()/1000)));
    return claim && {...claim,network:config.network,contractAddress:config.contractAddress,
      finalizedBlockHash:head.result!.slice(2),stateBlockHash:action.transaction.block.hash,checkedAt:new Date().toISOString(),
      trustBasis:'CONFIGURED_NODE_AND_INDEXER_WITH_PINNED_VERIFIER_KEYS'};
  } finally {clearTimeout(timer);}
}
