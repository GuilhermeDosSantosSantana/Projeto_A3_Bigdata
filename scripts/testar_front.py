"""Exercise the real GIRO UI in Edge, including writes to the local MySQL."""

from pathlib import Path
from uuid import uuid4

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidencias"
EVIDENCE.mkdir(exist_ok=True)


def main():
    errors = []
    sku = "UI-" + uuid4().hex[:8].upper()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto("http://127.0.0.1:3000/", wait_until="domcontentloaded")
        assert response and response.status == 200
        page.locator("#scale-customers").get_by_text("500.000").wait_for(timeout=60000)
        assert not any(word in page.locator("body").inner_text() for word in ("A3", "MySQL", "Redis"))
        page.screenshot(path=str(EVIDENCE / "giro_visao_geral.png"), full_page=True)

        page.locator('.nav-item[data-view="products"]').click()
        page.wait_for_function("document.querySelectorAll('#product-rows tr').length === 12", timeout=30000)
        assert page.locator("#product-rows tr").count() == 12
        page.locator("#products-next").click()
        page.locator("#products-page").get_by_text("Página 2").wait_for()
        page.locator("#products-prev").click()
        page.locator("#products-page").get_by_text("Página 1").wait_for()
        page.screenshot(path=str(EVIDENCE / "giro_produtos.png"), full_page=True)

        page.locator('.top-actions [data-action="product"]').click()
        assert page.locator('#action-dialog [name="id"]').count() == 0
        assert "automaticamente" in page.locator("#dialog-help").inner_text()
        page.locator('#action-dialog [name="sku"]').fill(sku)
        page.locator('#action-dialog [name="name"]').fill("Produto teste interface")
        page.locator('#action-dialog [name="min_stock"]').fill("5")
        page.locator('#action-dialog [name="sale_price"]').fill("14.90")
        page.locator("#submit-dialog").click()
        page.locator("#action-dialog").wait_for(state="hidden", timeout=30000)
        page.locator("#search").fill(sku)
        page.locator("#product-rows").get_by_text(sku).wait_for(timeout=30000)
        page.locator('#product-rows [data-detail-product]').first.click()
        page.locator("#detail-dialog").wait_for(state="visible")
        page.locator("#detail-body .detail-field").first.wait_for(timeout=10000)
        assert "Número interno" in page.locator("#detail-body").inner_text()
        assert sku in page.locator("#detail-subtitle").inner_text()
        page.screenshot(path=str(EVIDENCE / "giro_detalhe_produto.png"), full_page=True)

        page.locator('#detail-dialog [data-action="edit"]').click()
        page.locator('#action-dialog [name="min_stock"]').fill("6")
        page.locator("#submit-dialog").click()
        page.locator("#action-dialog").wait_for(state="hidden", timeout=30000)
        page.locator('#product-rows [data-action="receipt"]').click()
        page.locator('#action-dialog [name="quantity"]').fill("20")
        page.locator('#action-dialog [name="unit_cost"]').fill("9.50")
        page.locator('#action-dialog [name="expires_on"]').fill("2027-04-01")
        page.locator('#action-dialog [name="source_ref"]').fill("NF-" + sku)
        page.locator("#submit-dialog").click()
        page.locator("#action-dialog").wait_for(state="hidden", timeout=30000)
        page.locator('#product-rows [data-action="sale"]').click()
        page.locator('#action-dialog [name="quantity"]').fill("999")
        page.locator("#customer-search").fill("CLI-001")
        page.locator('[data-pick-customer="1"]').wait_for(timeout=10000)
        page.locator('[data-pick-customer="1"]').click()
        page.locator("#submit-dialog").click()
        page.get_by_text("Estoque insuficiente", exact=False).first.wait_for(timeout=10000)
        assert page.locator("#action-dialog").is_visible()
        page.locator('#action-dialog [name="quantity"]').fill("3")
        assert "44,70" in page.locator("#sale-preview").inner_text()
        page.screenshot(path=str(EVIDENCE / "giro_registro_venda.png"), full_page=True)
        page.locator("#submit-dialog").click()
        page.locator("#action-dialog").wait_for(state="hidden", timeout=30000)
        page.locator('#product-rows [data-detail-product]').first.click()
        page.locator("#detail-dialog").wait_for(state="visible")
        page.locator("#detail-body").get_by_text("17 un").wait_for(timeout=10000)
        body = page.locator("#detail-body").inner_text()
        assert "17 un" in body and "Lotes recebidos" in body and "Baixas recentes" in body
        page.locator("#close-detail").click()

        page.locator('.nav-item[data-view="overview"]').click()
        page.locator('[data-action="loss"]').click()
        page.locator("#product-search").fill(sku)
        page.locator("#product-results").get_by_text(sku).wait_for(timeout=10000)
        page.locator("#product-results [data-pick-product]").first.click()
        page.locator('#action-dialog [name="quantity"]').fill("2")
        page.locator('#action-dialog [name="reason"]').fill("Embalagem danificada")
        page.screenshot(path=str(EVIDENCE / "giro_registro_perda.png"))
        page.locator("#submit-dialog").click()
        page.locator("#action-dialog").wait_for(state="hidden", timeout=30000)

        page.locator('.nav-item[data-view="products"]').click()
        page.locator("#product-rows").get_by_text(sku).wait_for(timeout=30000)
        page.locator('#product-rows [data-detail-product]').first.click()
        page.locator("#detail-body").get_by_text("15 un").wait_for(timeout=10000)
        page.locator("#close-detail").click()

        page.locator('.nav-item[data-view="movements"]').click()
        page.locator("#movement-rows").get_by_text(sku).first.wait_for(timeout=30000)
        assert sku in page.locator("#movement-rows").inner_text()
        page.locator("#movement-filter").select_option("ENTRY")
        page.locator("#movement-rows").get_by_text("Entrada").first.wait_for()
        page.locator("#movement-filter").select_option("LOSS")
        page.locator("#movement-rows").get_by_text(sku).first.wait_for()
        page.screenshot(path=str(EVIDENCE / "giro_movimentacoes.png"), full_page=True)

        page.locator('.nav-item[data-view="customers"]').click()
        page.locator("#customer-directory-search").fill("CLI-001")
        page.locator('[data-detail-customer="1"]').wait_for(timeout=10000)
        page.locator('[data-detail-customer="1"]').click()
        page.locator("#detail-dialog").wait_for(state="visible")
        page.locator("#detail-body").get_by_text("Produto teste interface").first.wait_for(timeout=10000)
        assert "Produto teste interface" in page.locator("#detail-body").inner_text()
        page.screenshot(path=str(EVIDENCE / "giro_detalhe_cliente.png"), full_page=True)
        page.close()

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.on("pageerror", lambda error: errors.append(str(error)))
        mobile.goto("http://127.0.0.1:3000/", wait_until="domcontentloaded")
        mobile.locator("#scale-customers").get_by_text("500.000").wait_for(timeout=60000)
        assert mobile.locator('.nav-item[data-view="customers"]').is_visible()
        mobile.screenshot(path=str(EVIDENCE / "giro_mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()
    print(f"OK: navegacao, paginacao, cadastro {sku}, ID automatico, edicao, entrada, recusa por estoque, venda, perda, cliente e mobile")


if __name__ == "__main__":
    main()
