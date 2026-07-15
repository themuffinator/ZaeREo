"""Deterministic contracts for the stock-monster precache audit."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from audit_common import AuditError  # noqa: E402
from audit_stock_precaches import build_report, markdown_report  # noqa: E402


class StockPrecacheAuditTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, Path, Path, Path]:
        zaero = root / "zaero"
        legacy = root / "legacy"
        rerelease = root / "rerelease"
        port = root / "port"
        for path in (zaero, legacy, rerelease, port / "zaero"):
            path.mkdir(parents=True)

        (legacy / "m_alpha.c").write_text(
            'void SP_monster_alpha(void) { gi.soundindex("alpha.wav"); }\n',
            encoding="latin-1",
        )
        (zaero / "m_alpha.c").write_text(
            'void SP_monster_alpha_precache(void) { gi.soundindex("alpha.wav"); }\n'
            "void SP_monster_alpha(void) { SP_monster_alpha_precache(); }\n",
            encoding="latin-1",
        )
        (legacy / "m_infantry.c").write_text(
            'void SP_monster_infantry(void) { gi.soundindex("infantry.wav"); }\n',
            encoding="latin-1",
        )
        (zaero / "m_infantry.c").write_text(
            'void SP_monster_infantry_precache(void) { gi.soundindex("infantry.wav"); }\n'
            "void SP_monster_infantry(void) { SP_monster_infantry_precache(); }\n",
            encoding="latin-1",
        )
        (zaero / "z_handler.c").write_text(
            "void SP_monster_infantry_precache(void);\n"
            "void SP_monster_hound_precache(void);\n"
            "void SP_monster_handler_precache(void) {\n"
            " SP_monster_infantry_precache();\n"
            " SP_monster_hound_precache();\n"
            "}\n",
            encoding="latin-1",
        )
        (zaero / "q_shared.h").write_text(
            "#define MAX_SOUNDS 256\n", encoding="latin-1"
        )
        (zaero / "zaero.dsp").write_text(
            '# ADD CPP /D "WIN32" /D "NDEBUG"\n', encoding="latin-1"
        )
        (zaero / "g_main.c").write_text(
            "void setup(void) { gi.soundindex = internalSoundIndex; }\n",
            encoding="latin-1",
        )
        (zaero / "z_trigger.c").write_text(
            "void initSoundList(void) {\n"
            " soundList = gi.TagMalloc (sizeof(list_t), TAG_LEVEL);\n"
            " sound->name = gi.TagMalloc (strlen(name) + 1, TAG_LEVEL);\n"
            " name[i] = tolower(name[i]);\n"
            " if (numSounds >= MAX_SOUNDS-1) return 0;\n"
            "}\n",
            encoding="latin-1",
        )

        (rerelease / "game.h").write_text(
            "constexpr size_t MAX_SOUNDS = 2048;\n"
            "constexpr size_t MAX_MODELS_OLD = 256, MAX_SOUNDS_OLD = 256;\n",
            encoding="latin-1",
        )
        (rerelease / "g_turret.cpp").write_text(
            "void SP_turret_driver() { InfantryPrecache(); }\n",
            encoding="latin-1",
        )
        (rerelease / "m_infantry.cpp").write_text(
            "void InfantryPrecache() {}\n"
            "void SP_monster_infantry() { InfantryPrecache(); }\n",
            encoding="latin-1",
        )

        (port / "g_turret.cpp").write_text(
            "void SP_turret_driver() { InfantryPrecache(); }\n",
            encoding="utf-8",
        )
        (port / "m_infantry.cpp").write_text(
            "static cached_soundindex sound;\n"
            'void InfantryPrecache() { sound.assign("infantry.wav"); }\n'
            "void InfantryConvertFromZaeroHandler() { InfantryPrecache(); }\n"
            "void SP_monster_infantry() { InfantryPrecache(); }\n",
            encoding="utf-8",
        )
        (port / "zaero" / "g_zaero_handler.cpp").write_text(
            "namespace {\n"
            "static cached_soundindex sound;\n"
            "void handler_precache() { InfantryPrecache(); ZaeroHoundPrecache(); "
            'sound.assign("handler.wav"); }\n'
            "}\n",
            encoding="utf-8",
        )
        (port / "zaero" / "g_zaero_hound.cpp").write_text(
            "static cached_soundindex sound;\n"
            'void ZaeroHoundPrecache() { sound.assign("hound.wav"); }\n',
            encoding="utf-8",
        )
        return zaero, legacy, rerelease, port

    def test_report_finds_only_the_cross_file_infantry_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = build_report(*self.make_fixture(Path(temporary)))

        self.assertEqual(report["summary"]["helper_count"], 2)
        self.assertEqual(report["summary"]["source_file_count"], 2)
        self.assertEqual(report["summary"]["externally_reused_helper_count"], 1)
        external = [
            helper
            for helper in report["stock_precache_extractions"]
            if helper["external_call_sites"]
        ]
        self.assertEqual(external[0]["name"], "SP_monster_infantry_precache")
        self.assertEqual(external[0]["external_call_sites"][0]["path"], "z_handler.c")
        self.assertEqual(report["legacy_sound_index_context"]["zaero_max_sounds"], 256)
        self.assertEqual(report["legacy_sound_index_context"]["rerelease_max_sounds"], 2048)
        self.assertFalse(
            report["legacy_sound_index_context"]["cache_sound_workaround"]
            ["supplied_project_defines_cache_sound"]
        )
        markdown = markdown_report(report)
        self.assertIn("source/static evidence", markdown)
        self.assertIn("Full all-map resource", markdown)

    def test_unexpected_port_caller_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            inputs = self.make_fixture(Path(temporary))
            port = inputs[3]
            with (port / "m_infantry.cpp").open("a", encoding="utf-8") as stream:
                stream.write("void unrelated() { InfantryPrecache(); }\n")
            with self.assertRaisesRegex(AuditError, "call graph changed"):
                build_report(*inputs)


if __name__ == "__main__":
    unittest.main()
