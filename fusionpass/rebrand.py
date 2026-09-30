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
        if a in b and b in s:
            continue  # already applied; b extends a, so replacing again would repeat it
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
    val hidden = setOf(SettingsPage.ContentDiscovery, SettingsPage.Integrations, SettingsPage.TraktAuthentication, SettingsPage.Debrid)
    return entries.filterNot { e ->
        val p = (e.target as? SettingsSearchTarget.Page)?.page
        p != null && (p in hidden || p.parentPage in hidden)
    }
}

private data class PlaybackSearchRow("""),
])

# 9. Audio and subtitles (owner decision 2026-09-28): by default English audio, or Japanese for anime, with English
#    subtitles on. Nuvio defaults to the device language (Spanish on some dual-audio releases for Filipino-locale
#    phones) and subtitles off. The default is a setting of its own ("Auto"); a language the user picks still wins.
PL = f'{K}/features/player'
P = f'{PL}/PlayerSettingsRepository.kt'
edit(P, [
    ('    val preferredAudioLanguage: String = AudioLanguageOption.DEVICE,', '    val preferredAudioLanguage: String = AudioLanguageOption.FP_AUTO, // Fusion Pass'),
    ('    private var preferredAudioLanguage = AudioLanguageOption.DEVICE\n', '    private var preferredAudioLanguage = AudioLanguageOption.FP_AUTO // Fusion Pass\n'),
    ('        preferredAudioLanguage = AudioLanguageOption.DEVICE\n        secondaryPreferredAudioLanguage = null', '        preferredAudioLanguage = AudioLanguageOption.FP_AUTO // Fusion Pass\n        secondaryPreferredAudioLanguage = null'),
    ('            normalizeLanguageCode(PlayerSettingsStorage.loadPreferredAudioLanguage())\n                ?: AudioLanguageOption.DEVICE', '            normalizeLanguageCode(PlayerSettingsStorage.loadPreferredAudioLanguage())\n                ?: AudioLanguageOption.FP_AUTO // Fusion Pass'),
    ('    val preferredSubtitleLanguage: String = SubtitleLanguageOption.NONE,', '    val preferredSubtitleLanguage: String = "en", // Fusion Pass: English subtitles on'),
    ('    private var preferredSubtitleLanguage = SubtitleLanguageOption.NONE\n', '    private var preferredSubtitleLanguage = "en" // Fusion Pass\n'),
    ('        preferredSubtitleLanguage = SubtitleLanguageOption.NONE\n        secondaryPreferredSubtitleLanguage = null', '        preferredSubtitleLanguage = "en" // Fusion Pass\n        secondaryPreferredSubtitleLanguage = null'),
    ('            normalizeLanguageCode(PlayerSettingsStorage.loadPreferredSubtitleLanguage())\n                ?: SubtitleLanguageOption.NONE', '            normalizeLanguageCode(PlayerSettingsStorage.loadPreferredSubtitleLanguage())\n                ?: "en" // Fusion Pass'),
])
edit(f'{PL}/PlayerLanguagePreferences.kt', [
    ('    const val ORIGINAL = "original"\n}\n', '    const val ORIGINAL = "original"\n    const val FP_AUTO = "fpauto" // Fusion Pass: English, Japanese for anime (same value in every app: settings sync)\n    const val FP_AUTO_LABEL = "Auto (English, Japanese for anime)"\n}\n'),
    ('    contentOriginalLanguage: String? = null,\n): List<String> {', '    contentOriginalLanguage: String? = null,\n    isAnime: Boolean = false, // Fusion Pass\n): List<String> {'),
    ('    return when (primary) {\n        AudioLanguageOption.DEFAULT -> listOfNotNull(\n            normalize(secondaryPreferredAudioLanguage),\n        ).distinct()\n',
     '    return when (primary) {\n        AudioLanguageOption.FP_AUTO -> listOfNotNull(\n            "ja".takeIf { isAnime }, "en", normalize(secondaryPreferredAudioLanguage),\n        ).distinct() // Fusion Pass\n\n        AudioLanguageOption.DEFAULT -> listOfNotNull(\n            normalize(secondaryPreferredAudioLanguage),\n        ).distinct()\n'),
    ('    code.equals(AudioLanguageOption.DEFAULT, ignoreCase = true) ->\n        stringResource(Res.string.settings_playback_option_default)',
     '    code.equals(AudioLanguageOption.FP_AUTO, ignoreCase = true) -> AudioLanguageOption.FP_AUTO_LABEL // Fusion Pass\n    code.equals(AudioLanguageOption.DEFAULT, ignoreCase = true) ->\n        stringResource(Res.string.settings_playback_option_default)'),
    ('    code.equals(AudioLanguageOption.DEFAULT, ignoreCase = true) ->\n        getString(Res.string.settings_playback_option_default)',
     '    code.equals(AudioLanguageOption.FP_AUTO, ignoreCase = true) -> AudioLanguageOption.FP_AUTO_LABEL // Fusion Pass\n    code.equals(AudioLanguageOption.DEFAULT, ignoreCase = true) ->\n        getString(Res.string.settings_playback_option_default)'),
])
edit(f'{PL}/PlayerScreenRuntimeAudioPreferences.kt', [
    ('        contentOriginalLanguage = contentLanguage,\n    )\n', '        contentOriginalLanguage = contentLanguage,\n        isAnime = fpIsAnime, // Fusion Pass\n    )\n'),
])
FP_ANIME = '''package com.nuvio.app.features.player

// Fusion Pass: anime detection for the "Auto" audio default (Japanese audio; English subtitles come
// from the subtitle default). Written by fusionpass/rebrand.py.
internal val PlayerScreenRuntime.fpIsAnime: Boolean
    get() {
        val ids = listOfNotNull(activeVideoId, parentMetaId)
        if (ids.any { id -> listOf("kitsu:", "mal:", "anilist:", "anidb:").any { id.startsWith(it) } }) return true
        val meta = listOfNotNull(metaUiState.meta, playerMeta).firstOrNull { it.id == parentMetaId }
        val genres = meta?.genres.orEmpty()
        if (genres.any { it.equals("anime", ignoreCase = true) }) return true
        val animation = genres.any { it.equals("animation", ignoreCase = true) }
        return animation && (meta?.country?.contains("Japan", ignoreCase = true) == true || contentLanguage == "ja")
    }
'''
if not os.path.exists(f'{PL}/FusionPassAnimeAudio.kt') or open(f'{PL}/FusionPassAnimeAudio.kt', encoding='utf8').read() != FP_ANIME:
    open(f'{PL}/FusionPassAnimeAudio.kt', 'w', encoding='utf8').write(FP_ANIME)
    changed.append('features/player/FusionPassAnimeAudio.kt')
edit(f'{K}/features/settings/PlaybackSettingsPage.kt', [
    ('                        AudioLanguageOption.DEFAULT -> stringResource(Res.string.settings_playback_option_default)\n',
     '                        AudioLanguageOption.FP_AUTO -> AudioLanguageOption.FP_AUTO_LABEL // Fusion Pass\n                        AudioLanguageOption.DEFAULT -> stringResource(Res.string.settings_playback_option_default)\n'),
    ('            options = listOf(\n                LanguageSelectionOption(AudioLanguageOption.DEFAULT, stringResource(Res.string.settings_playback_option_default)),\n                LanguageSelectionOption(AudioLanguageOption.DEVICE,',
     '            options = listOf(\n                LanguageSelectionOption(AudioLanguageOption.FP_AUTO, AudioLanguageOption.FP_AUTO_LABEL), // Fusion Pass\n                LanguageSelectionOption(AudioLanguageOption.DEFAULT, stringResource(Res.string.settings_playback_option_default)),\n                LanguageSelectionOption(AudioLanguageOption.DEVICE,'),
])

# No debrid names anywhere (owner 2026-09-28): the account's sources are ours, so the cloud library
# (connect TorBox / Premiumize), their credits on Licenses, and the Connected Services page are gone.
import re as _re
def drop(path, pattern, what):
    s = open(path, encoding='utf8').read()
    n = _re.subn(pattern, '', s, flags=_re.S)
    if n[1] == 0 and not _re.search(r'Fusion Pass: no debrid', s):
        sys.exit(f'rebrand: {what} not found in {path} (upstream changed; update rebrand.py)')
    if n[1]:
        s = n[0]
        if 'Fusion Pass: no debrid' not in s:
            s = s.rstrip('\n') + '\n// Fusion Pass: no debrid credits or rows (rebrand.py)\n'
        open(path, 'w', encoding='utf8').write(s)
        changed.append(os.path.relpath(path, ROOT))
drop(f'{K}/features/settings/LicensesAttributionsPage.kt',
     r'    AttributionItem\(\n        titleRes = Res\.string\.settings_licenses_attributions_(?:premiumize|torbox)_title,.*?\n    \),\n',
     'Premiumize/TorBox attribution items')
drop(f'{K}/features/settings/SettingsSearch.kt',
     r'        PlaybackSearchRow\("(?:premiumize|torbox)-attribution".*?\n', 'Premiumize/TorBox search rows')
edit(f'{K}/features/library/LibraryScreen.kt', [
    ('private fun LibrarySourceSwitch(\n    selectedMode: LibraryViewMode,\n    onModeSelected: (LibraryViewMode) -> Unit,\n    modifier: Modifier = Modifier,\n) {\n',
     'private fun LibrarySourceSwitch(\n    selectedMode: LibraryViewMode,\n    onModeSelected: (LibraryViewMode) -> Unit,\n    modifier: Modifier = Modifier,\n) {\n    if (true) return // Fusion Pass: no cloud library (debrid accounts)\n'),
])

# In-app updates: compare the -fp<N> revision numerically (code review 2026-09-29, report 22 F2).
edit(f'{K}/features/updater/VersionUtils.kt', [('    private fun comparePrereleaseIdentifier(left: String, right: String): Int {\n', '    private fun comparePrereleaseIdentifier(left: String, right: String): Int {\n        // Fusion Pass: tags end in -fp<N>. Compare that revision as a number, or "fp10" sorts below\n        // "fp9" and every device stops updating at fp9 (code review 2026-09-29, report 22 F2).\n        val fpRev = Regex("^(.*?)fp(\\\\d+)$")\n        val fpLeft = fpRev.matchEntire(left)\n        val fpRight = fpRev.matchEntire(right)\n        if (fpLeft != null && fpRight != null && fpLeft.groupValues[1] == fpRight.groupValues[1]) {\n            return compareValues(fpLeft.groupValues[2].toLong(), fpRight.groupValues[2].toLong())\n        }\n')])

# Addon-install deep links do nothing: the pass manages the addons (code review 2026-09-29, report 22 F4).
edit(f'{K}/MainAppContent.kt', [('                    is AppDeepLink.AddonInstall -> {\n                        activateTab(AppScreenTab.Settings)\n                        navController.navigate(AddonsSettingsRoute(addonsSettingsTitle)) {\n                            launchSingleTop = true\n                        }\n                        NuvioToastController.show(getString(Res.string.addons_modal_checking_title))\n                        AddonRepository.initialize()\n                        when (val result = AddonRepository.addAddon(deepLink.manifestUrl)) {\n                            is AddAddonResult.Success -> {\n                                NuvioToastController.show(\n                                    getString(Res.string.addons_modal_success_message, result.manifest.name),\n                                )\n                            }\n\n                            is AddAddonResult.Error -> {\n                                NuvioToastController.show(result.message)\n                            }\n                        }\n                        AppDeepLinkRepository.markConsumed(deepLink)\n                    }', '                    is AppDeepLink.AddonInstall -> {\n                        // Fusion Pass: addons are managed by the pass; a stremio:// or nuvio://<host> link\n                        // must not install one or open the hidden addon settings (review 22 F4).\n                        AppDeepLinkRepository.markConsumed(deepLink)\n                    }')])

print('rebrand: ok,', len(changed), 'changes')
for c in changed[:40]:
    print('  ', c)
