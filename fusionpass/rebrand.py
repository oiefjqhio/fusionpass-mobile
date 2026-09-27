#!/usr/bin/env python3
"""Apply the Fusion Pass branding and lock-down to a NuvioMobile checkout (Android build).
Idempotent: run after every upstream sync (git merge upstream/cmp-rewrite, then this, commit).

GPL-3.0: this fork's source stays public; README and About credit Nuvio.
"""
import glob, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = f'{ROOT}/composeApp/src'
RES = f'{APP}/androidMain/res'
CR = f'{APP}/commonMain/composeResources'
K = f'{APP}/commonMain/kotlin/com/nuvio/app'
OUT = f'{ROOT}/fusionpass/brand/out'
changed = []


def edit(path, pairs):
    s = open(path, encoding='utf8').read()
    orig = s
    for a, b in pairs:
        if a not in s and b not in s:
            sys.exit(f'rebrand: anchor not found in {path}: {a[:80]!r} (upstream changed; update rebrand.py)')
        s = s.replace(a, b)
    if s != orig:
        open(path, 'w', encoding='utf8').write(s)
        changed.append(os.path.relpath(path, ROOT))


def put(src, dst_no_ext):
    """Write our PNG at dst (.png), removing a same-named .webp so the resource is not duplicated."""
    for old in glob.glob(dst_no_ext + '.webp'):
        os.remove(old)
        changed.append(os.path.relpath(old, ROOT) + ' (removed)')
    dst = dst_no_ext + '.png'
    if not os.path.exists(dst) or open(dst, 'rb').read() != open(src, 'rb').read():
        shutil.copyfile(src, dst)
        changed.append(os.path.relpath(dst, ROOT))


# 1. Launcher icons (every alternate variant too), adaptive layers, splash, in-app logos.
for d in ['mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi']:
    for f in glob.glob(f'{RES}/mipmap-{d}/ic_launcher*.webp') + glob.glob(f'{RES}/mipmap-{d}/ic_launcher*.png'):
        base = os.path.splitext(f)[0]
        name = os.path.basename(base)
        if name.endswith('_foreground'):
            src = f'{OUT}/ic_launcher_foreground-{d}.png'
        elif name.endswith('_monochrome'):
            src = f'{OUT}/ic_launcher_monochrome-{d}.png'
        elif name.endswith('_round'):
            src = f'{OUT}/ic_launcher_round-{d}.png'
        else:
            src = f'{OUT}/ic_launcher-{d}.png'
        put(src, base)
for f in glob.glob(f'{RES}/drawable-nodpi/ic_splash_logo*.webp') + glob.glob(f'{RES}/drawable-nodpi/ic_splash_logo*.png'):
    put(f'{OUT}/ic_splash_logo.png', os.path.splitext(f)[0])
for f in glob.glob(f'{CR}/drawable/app_icon_*.png'):
    put(f'{OUT}/app_icon_original.png', os.path.splitext(f)[0])
for f in glob.glob(f'{CR}/drawable/app_logo_wordmark*.png'):
    put(f'{OUT}/app_logo_wordmark.png', os.path.splitext(f)[0])
edit(f'{RES}/values/colors.xml', [('<color name="app_icon_background">#000000</color>', '<color name="app_icon_background">#6B6CFF</color>')])

# 2. Visible text: Nuvio -> Fusion Pass in every language.
for path in glob.glob(f'{CR}/values*/strings.xml') + glob.glob(f'{RES}/values*/strings.xml'):
    s = open(path, encoding='utf8').read()
    n = re.sub(r'(<(?:string|item)[^>]*>)([^<]*)(<)', lambda m: m.group(1) + m.group(2).replace('Nuvio', 'Fusion Pass') + m.group(3), s)
    if n != s:
        open(path, 'w', encoding='utf8').write(n)
        changed.append(os.path.relpath(path, ROOT))

# 3. Our app id and update channel.
edit(f'{ROOT}/androidApp/build.gradle.kts', [('        applicationId = "com.nuvio.app"\n', '        applicationId = "shop.fusionpass.app"\n')])
edit(f'{K}/features/updater/AppUpdaterRepository.kt', [
    ('"https://api.github.com/repos/NuvioMedia/NuvioMobile/', '"https://api.github.com/repos/oiefjqhio/fusionpass-mobile/'),
])

# 4. Lock-down for the Android full build: never P2P (owner rule), no plugins, no donation or
#    supporter pages for another project under our name, no custom servers.
edit(f'{APP}/androidFull/kotlin/com/nuvio/app/core/build/AppFeaturePolicy.android.kt', [
    ('actual val pluginsEnabled: Boolean = true', 'actual val pluginsEnabled: Boolean = false'),
    ('actual val supportersContributorsPageEnabled: Boolean = true', 'actual val supportersContributorsPageEnabled: Boolean = false'),
    ('actual val donationActionsEnabled: Boolean = true', 'actual val donationActionsEnabled: Boolean = false'),
    ('actual val p2pEnabled: Boolean = true', 'actual val p2pEnabled: Boolean = false'),
    ('actual val customServerConnectionsEnabled: Boolean = true', 'actual val customServerConnectionsEnabled: Boolean = false'),
])

# 5. The account comes fully configured: no addon manager, no debrid/metadata integrations.
edit(f'{K}/features/settings/SettingsRootPage.kt', [
    ('''                    SettingsNavigationRow(
                        title = stringResource(Res.string.compose_settings_page_content_discovery),
                        description = stringResource(Res.string.compose_settings_root_content_discovery_description),
                        icon = Icons.Rounded.Extension,
                        isTablet = isTablet,
                        onClick = onContentDiscoveryClick,
                    )
                    SettingsGroupDivider(isTablet = isTablet)
''', '''                    // Fusion Pass: addons come with the account (content discovery row removed)
'''),
    ('''                    SettingsNavigationRow(
                        title = stringResource(Res.string.compose_settings_page_integrations),
                        description = stringResource(Res.string.compose_settings_root_integrations_description),
                        icon = Icons.Rounded.Link,
                        isTablet = isTablet,
                        onClick = onIntegrationsClick,
                    )
                    SettingsGroupDivider(isTablet = isTablet)
''', '''                    // Fusion Pass: no debrid/metadata integrations (integrations row removed)
'''),
])

# 6. Our own links.
edit(f'{K}/features/settings/SettingsRootPage.kt', [('"https://nuvio.tv/privacy-policy"', '"https://fusionpass.shop/privacy"')])
edit(f'{K}/features/auth/AuthScreen.kt', [('"https://nuvio.tv/terms"', '"https://fusionpass.shop/terms"')])
edit(f'{K}/core/auth/DeviceLinkAuthRepository.kt', [('"https://nuvio.tv/link"', '"https://sync.fusionpass.shop/link"')])

# 7. Names a user can see outside the string resources.
edit(f'{K}/features/settings/TrackingProviderCards.kt', [('    NUVIO("Nuvio"),', '    NUVIO("Fusion Pass"),')])
edit(f'{K}/features/library/LibraryRepository.kt', [('DEFAULT_LOCAL_LIBRARY_TAB_TITLE = "Nuvio Library"', 'DEFAULT_LOCAL_LIBRARY_TAB_TITLE = "Library"')])
edit(f'{K}/core/auth/DeviceSessionRegistration.kt', [('CLIENT_NAME = "Nuvio Mobile"', 'CLIENT_NAME = "Fusion Pass Mobile"')])

# 8. No tracking services (Trakt/Simkl need our own API apps; owner chose to hide them). Library and
#    watch progress stay on our sync server. Settings search must not reopen any hidden page.
edit(f'{K}/features/settings/SettingsRootPage.kt', [
    ("""                    SettingsGroupDivider(isTablet = isTablet)
                    SettingsNavigationRow(
                        title = stringResource(Res.string.compose_settings_page_tracking),
                        description = stringResource(Res.string.compose_settings_root_tracking_description),
                        icon = Icons.Default.Sync,
                        isTablet = isTablet,
                        onClick = onTrackingClick,
                    )
""", """                    // Fusion Pass: tracking services row removed
"""),
])
edit(f'{K}/features/settings/SettingsSearch.kt', [
    ("""    return entries
}

private data class PlaybackSearchRow(""", """    // Fusion Pass: pages removed from the settings root stay out of search too.
    val hidden = setOf(SettingsPage.ContentDiscovery, SettingsPage.Integrations, SettingsPage.TraktAuthentication)
    return entries.filterNot { e ->
        val p = (e.target as? SettingsSearchTarget.Page)?.page
        p != null && (p in hidden || p.parentPage in hidden)
    }
}

private data class PlaybackSearchRow("""),
])

print('rebrand: ok,', len(changed), 'changes')
for c in changed[:40]:
    print('  ', c)
