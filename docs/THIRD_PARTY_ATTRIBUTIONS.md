# Third-party source attribution

The Midnight compatibility package adapts the local wallet/provider setup from
[midnightntwrk/example-hello-world](https://github.com/midnightntwrk/example-hello-world),
revision `fa01af37511e955672f484af6f1ef31cb6509798`, under Apache-2.0.
The upstream license is retained at
`packages/compact-contracts/vendor/midnight-hello-world/LICENSE`.
No upstream NOTICE file was present in that revision.

Modified source files contain attribution comments. TeaPass removes wallet secret-prefix
logging, limits this harness to synthetic local devnet use, separates receipt evidence from
private state, and provides its own contract rules and negative tests. Starter plumbing
is not claimed as TeaPass protocol innovation.
