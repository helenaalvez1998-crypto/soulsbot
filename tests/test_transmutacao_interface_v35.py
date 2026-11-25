from pathlib import Path
import unittest

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from site_hub import registrar_rotas


class FakeBot:
    db = None

    def _api_user_id(self, request):
        return None

    def _api_origin_ok(self, request):
        return True


class TransmutacaoInterfaceV35Tests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        app = web.Application()
        registrar_rotas(FakeBot(), app)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_page_and_api_routes_registered(self):
        response = await self.client.get('/transmutacao')
        self.assertEqual(response.status, 200)
        body = await response.text()
        self.assertIn('LABORATÓRIO DE TRANSMUTAÇÃO', body)
        self.assertIn('sacrifício irreversível', body.lower())

    async def test_private_endpoints_require_authentication(self):
        for path in (
            '/api/gwent/transmutacao',
            '/api/gwent/cartas-geradas',
            '/api/gwent/cartas-geradas/nao-existe',
        ):
            response = await self.client.get(path)
            self.assertEqual(response.status, 401, path)
        for path in (
            '/api/gwent/transmutacao/preview',
            '/api/gwent/transmutacao/execute',
        ):
            response = await self.client.post(path, json={})
            self.assertEqual(response.status, 401, path)

    def test_page_explains_personal_card_protection_and_confirmation(self):
        html = (Path(__file__).resolve().parents[1] / 'site' / 'transmutacao.html').read_text()
        self.assertIn('exclusivas da sua conta', html)
        self.assertIn('Confirmar transmutação', html)
        self.assertIn("confirmed:true", html)
        self.assertIn("/api/gwent/transmutacao/preview", html)
        self.assertIn("/api/gwent/transmutacao/execute", html)


if __name__ == '__main__':
    unittest.main()
