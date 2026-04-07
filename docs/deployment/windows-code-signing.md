# Windows Code Signing

This repo can sign the Windows launcher and installer with Azure Artifact Signing so Windows shows a real publisher instead of the usual unsigned-app melodrama.

## What The Workflow Signs

- `dist/windows-installer/input/LoRAPilotLauncher.exe`
- `dist/windows-installer/LoRAPilotSetup.exe`

`Install-LoRAPilotPreview.ps1` is not part of the current signing flow. Keep that in mind before pretending PowerShell will be chill about it.

## Recommended Setup

Use Azure Artifact Signing with GitHub Actions OIDC. It keeps the key material out of the repo and out of your laptop, which is the bare minimum for an adult signing setup.

### Azure prerequisites

- Artifact Signing account
- completed identity validation for the publisher you want Windows to show
- certificate profile
- `Artifact Signing Certificate Profile Signer` role assigned to the GitHub Actions app identity
- GitHub OIDC federated credential on the Azure app registration used by the workflow

### Repo or org variables

- `WINDOWS_SIGNING_ENDPOINT`
- `WINDOWS_SIGNING_ACCOUNT_NAME`
- `WINDOWS_SIGNING_CERTIFICATE_PROFILE_NAME`

Example endpoint values are region-specific, for example `https://weu.codesigning.azure.net` or `https://neu.codesigning.azure.net`. Use the region that matches the Artifact Signing account or enjoy 403s.

### Repo or org secrets

OIDC path:

- `WINDOWS_SIGNING_AZURE_CLIENT_ID`
- `WINDOWS_SIGNING_AZURE_TENANT_ID`
- `WINDOWS_SIGNING_AZURE_SUBSCRIPTION_ID` optional, only if the Azure login needs a subscription context

Fallback client-secret path:

- `WINDOWS_SIGNING_AZURE_CLIENT_SECRET`

If `WINDOWS_SIGNING_AZURE_CLIENT_SECRET` is present, the workflow uses it as the fallback auth path. If it is absent, the workflow uses OIDC through `azure/login`.

## Workflow Behavior

The Windows installer workflow now does this:

1. Build `LoRAPilotLauncher.exe`
2. Build `LoRAPilotSetup.exe`
3. Detect signing configuration
4. Sign both executables when signing is configured
5. Verify both signatures with `Get-AuthenticodeSignature`
6. Upload or publish the signed installer

If signing config is incomplete, the build still succeeds and publishes an unsigned installer. That is deliberate. Preview builds should not explode just because certificate plumbing is absent.

## Publisher And Trust Notes

- The Windows publisher name comes from the validated identity on the signing certificate profile.
- Timestamping uses `http://timestamp.acs.microsoft.com/`.
- Signed does not mean SmartScreen instantly loves you. Reputation still has to accumulate like every other mildly inconvenient truth.

## Related Files

- `.github/workflows/windows-installer.yml`
- `packaging/windows/build-installer.ps1`
- `docs/deployment/windows-preview-release-template.md`

## References

- Azure Artifact Signing overview: https://learn.microsoft.com/en-us/azure/artifact-signing/overview
- Azure Artifact Signing integrations: https://learn.microsoft.com/en-us/azure/artifact-signing/how-to-signing-integrations
- Trusted Signing GitHub Action: https://github.com/marketplace/actions/trusted-signing
