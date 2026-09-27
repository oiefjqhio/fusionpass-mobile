# Fusion Pass (phone)

Fusion Pass for Android phones and tablets. This is a fork of [Nuvio Mobile](https://github.com/NuvioMedia/NuvioMobile)
(GPL-3.0). All changes live in this `fusionpass/` folder plus what `rebrand.py` writes, so this source
stays public under the same licence.

- Signs in to the Fusion Pass account service (`sync.fusionpass.shop`, a Nuvio self-host) with email and password.
- Plugins and custom servers are off; everything is set up by the account.
- Updates come from this repository's releases.

## Syncing with upstream

```sh
git fetch upstream
git merge upstream/cmp-rewrite
python3 fusionpass/rebrand.py   # exits with an error if an anchor moved upstream
git commit -am "Sync upstream and re-apply branding"
git push
```

Then run the **Fusion Pass (phone) release** workflow (Actions tab) with the next `rev`.

## Brand assets

`brand/render.mjs` renders `brand/out/*.png` from `brand/logo.svg` and League Spartan (playwright-core).
