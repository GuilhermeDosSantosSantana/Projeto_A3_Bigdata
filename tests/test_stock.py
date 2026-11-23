"""Testes de integridade para executar quando o grupo autorizar a validação."""

import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from giro import db


class StockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_path = db.DB_PATH
        db.DB_PATH = Path(self.temp.name) / "giro.sqlite3"
        db.initialize()
        self.product_id = db.add_product({
            "sku": "TST-999", "name": "Produto de teste", "category_id": 1,
            "supplier_id": 1, "unit": "un", "min_stock": 2,
            "lead_days": 3, "sale_price_cents": 1000,
        })

    def tearDown(self):
        db.DB_PATH = self.original_path
        self.temp.cleanup()

    def test_venda_consome_lote_mais_proximo_e_atualiza_saldo(self):
        late = db.add_receipt({
            "product_id": self.product_id, "quantity": 3, "unit_cost_cents": 400,
            "expires_on": (date.today() + timedelta(days=12)).isoformat(),
            "source_ref": "TST-LATE",
        })
        early = db.add_receipt({
            "product_id": self.product_id, "quantity": 3, "unit_cost_cents": 400,
            "expires_on": (date.today() + timedelta(days=3)).isoformat(),
            "source_ref": "TST-EARLY",
        })
        db.add_sale({"product_id": self.product_id, "quantity": 5})
        with db.database() as conn:
            consumed = dict(conn.execute(
                "SELECT batch_id, SUM(quantity) FROM stock_event WHERE batch_id IN (?,?) GROUP BY batch_id",
                (early, late),
            ).fetchall())
            stock = conn.execute("SELECT stock FROM product_balance WHERE id = ?", (self.product_id,)).fetchone()[0]
        self.assertEqual(consumed[early], 3)
        self.assertEqual(consumed[late], 2)
        self.assertEqual(stock, 1)

    def test_venda_sem_saldo_nao_grava_venda(self):
        with db.database() as conn:
            before = conn.execute("SELECT COUNT(*) FROM sale").fetchone()[0]
        with self.assertRaisesRegex(ValueError, "insuficiente"):
            db.add_sale({"product_id": self.product_id, "quantity": 1})
        with db.database() as conn:
            after = conn.execute("SELECT COUNT(*) FROM sale").fetchone()[0]
        self.assertEqual(before, after)

    def test_referencia_duplicada_e_bloqueada(self):
        receipt = {"product_id": self.product_id, "quantity": 2,
                   "unit_cost_cents": 400, "source_ref": "NF-TESTE"}
        db.add_receipt(receipt)
        with self.assertRaises(sqlite3.IntegrityError):
            db.add_receipt(receipt)

    def test_gatilho_impede_saldo_negativo_mesmo_em_sql_direto(self):
        batch_id = db.add_receipt({"product_id": self.product_id, "quantity": 2,
                                   "unit_cost_cents": 400})
        with self.assertRaises(sqlite3.IntegrityError):
            with db.database() as conn:
                conn.execute("INSERT INTO stock_event(batch_id,kind,quantity,reason) VALUES (?,?,?,?)",
                             (batch_id, "LOSS", 3, "Avaria de teste"))

    def test_lote_vencido_nao_pode_ser_vendido_mas_pode_ter_baixa(self):
        with db.database() as conn:
            conn.execute("INSERT INTO batch(product_id,quantity_received,unit_cost_cents,expires_on) VALUES (?,?,?,?)",
                         (self.product_id, 2, 400, (date.today() - timedelta(days=1)).isoformat()))
        with self.assertRaisesRegex(ValueError, "insuficiente"):
            db.add_sale({"product_id": self.product_id, "quantity": 1})
        db.add_loss({"product_id": self.product_id, "quantity": 2, "reason": "Validade expirada"})
        with db.database() as conn:
            remaining = conn.execute("SELECT SUM(available_quantity) FROM batch_balance WHERE product_id = ?",
                                     (self.product_id,)).fetchone()[0]
        self.assertEqual(remaining, 0)


if __name__ == "__main__":
    unittest.main()
