import unittest

from configurar_bot import atualizar_env_texto, ler_valor_existente


class ConfiguradorEnvTests(unittest.TestCase):
    def test_atualiza_valor_preservando_comentarios(self):
        original = "# comentário importante\nDISCORD_TOKEN=antigo\nGUILD_ID=123\n"
        novo = atualizar_env_texto(original, {"DISCORD_TOKEN": "novo", "GUILD_ID": "456"})
        self.assertIn("# comentário importante", novo)
        self.assertIn("DISCORD_TOKEN=novo", novo)
        self.assertIn("GUILD_ID=456", novo)
        self.assertNotIn("DISCORD_TOKEN=antigo", novo)

    def test_remove_duplicatas_da_mesma_chave(self):
        original = "A=1\nA=2\nB=3\n"
        novo = atualizar_env_texto(original, {"A": "9"})
        self.assertEqual(novo.count("A="), 1)
        self.assertIn("A=9", novo)
        self.assertIn("B=3", novo)

    def test_adiciona_chave_ausente(self):
        novo = atualizar_env_texto("A=1\n", {"B": "2"})
        self.assertTrue(novo.endswith("B=2\n"))

    def test_le_valor_com_aspas(self):
        self.assertEqual(ler_valor_existente('GEMINI_API_KEY="abc-123"\n', "GEMINI_API_KEY"), "abc-123")

    def test_nao_confunde_nome_de_chave(self):
        texto = "GEMINI_API_KEY_BACKUP=backup\nGEMINI_API_KEY=primary\n"
        self.assertEqual(ler_valor_existente(texto, "GEMINI_API_KEY"), "primary")


if __name__ == "__main__":
    unittest.main()

class ConfiguradorFluxoTests(unittest.TestCase):
    def test_main_cria_env_sem_exibir_credenciais(self):
        import contextlib
        import io
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import configurar_bot

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_path = root / ".env"
            template = root / "env.example"
            template.write_text("DISCORD_TOKEN=\nGEMINI_API_KEY=\nGEMINI_BACKUP_API_KEY=\nGUILD_ID=0\n", encoding="utf-8")
            saida = io.StringIO()
            with patch.object(configurar_bot, "ROOT", root), \
                 patch.object(configurar_bot, "ENV_PATH", env_path), \
                 patch.object(configurar_bot, "TEMPLATE_CANDIDATES", (template,)), \
                 patch.object(configurar_bot.getpass, "getpass", side_effect=["discord-secret", "gemini-secret", "", "", ""]), \
                 patch("builtins.input", return_value="123456"), \
                 contextlib.redirect_stdout(saida):
                resultado = configurar_bot.main()

            self.assertEqual(resultado, 0)
            gravado = env_path.read_text(encoding="utf-8")
            self.assertIn("DISCORD_TOKEN=discord-secret", gravado)
            self.assertIn("GEMINI_API_KEY=gemini-secret", gravado)
            self.assertIn("NARA_CONVERSA_ENABLED=true", gravado)
            self.assertIn("NARA_CHAT_IA_ENABLED=false", gravado)
            self.assertNotIn("discord-secret", saida.getvalue())
            self.assertNotIn("gemini-secret", saida.getvalue())

    def test_main_avisa_quando_nao_ha_chave_gemini(self):
        import contextlib
        import io
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import configurar_bot

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_path = root / ".env"
            template = root / "env.example"
            template.write_text("DISCORD_TOKEN=\nGEMINI_API_KEY=\nGEMINI_BACKUP_API_KEY=\nGUILD_ID=0\n", encoding="utf-8")
            with patch.object(configurar_bot, "ROOT", root), \
                 patch.object(configurar_bot, "ENV_PATH", env_path), \
                 patch.object(configurar_bot, "TEMPLATE_CANDIDATES", (template,)), \
                 patch.object(configurar_bot.getpass, "getpass", side_effect=["discord-secret", "", "", "", ""]), \
                 patch("builtins.input", return_value="0"), \
                 contextlib.redirect_stdout(io.StringIO()):
                resultado = configurar_bot.main()

            self.assertEqual(resultado, 1)
            self.assertTrue(env_path.exists())
            self.assertIn("NARA_CONVERSA_ENABLED=true", env_path.read_text(encoding="utf-8"))

