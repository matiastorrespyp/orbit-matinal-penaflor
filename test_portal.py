"""
Test script para ORBIT PAV Matinal Peñaflor
Captura screenshots del portal rediseñado
"""
from playwright.sync_api import sync_playwright
import os, time

OUT = r"C:\Orbit\MATINAL_PENAFLOR\screenshots"
os.makedirs(OUT, exist_ok=True)

errors = []

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome", args=["--window-size=1440,900"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # Capturar errores de consola
        page.on("console", lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)

        print("→ Navegando al portal...")
        page.goto("http://localhost:8502/portal.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)

        # 1. Login screen
        page.screenshot(path=f"{OUT}/01_login.png", full_page=False)
        print("✓ 01_login.png")

        # 2. Login como gerencia
        page.select_option("#userSelect", "gerencia")
        page.fill("#pwdInput", "gerencia2026")
        page.click(".ln-btn")
        page.wait_for_timeout(2500)  # esperar carga de datos
        page.screenshot(path=f"{OUT}/02_gerencia_dashboard.png", full_page=False)
        print("✓ 02_gerencia_dashboard.png")

        # 3. Navegar a Vendedores
        page.click('[data-sc="vendedores"]')
        page.wait_for_timeout(600)
        page.screenshot(path=f"{OUT}/03_gerencia_vendedores.png", full_page=False)
        print("✓ 03_gerencia_vendedores.png")

        # 4. Navegar a Alertas
        page.click('[data-sc="alertas"]')
        page.wait_for_timeout(600)
        page.screenshot(path=f"{OUT}/04_gerencia_alertas.png", full_page=False)
        print("✓ 04_gerencia_alertas.png")

        # 5. Cerrar sesión
        page.click("text=Salir")
        page.wait_for_timeout(500)

        # Login como vendedor V3 (mobile view — viewport 390px)
        ctx2 = browser.new_context(viewport={"width": 390, "height": 844}, user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
        page2 = ctx2.new_page()
        page2.on("console", lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)

        page2.goto("http://localhost:8502/portal.html")
        page2.wait_for_load_state("networkidle")
        page2.wait_for_timeout(600)

        page2.select_option("#userSelect", "v3")
        page2.fill("#pwdInput", "pav2026")
        page2.click(".ln-btn")
        page2.wait_for_timeout(2500)

        # 6. Inicio vendedor
        page2.screenshot(path=f"{OUT}/05_vendedor_inicio.png", full_page=False)
        print("✓ 05_vendedor_inicio.png")

        # 7. Tab Ruta — usar selector específico del bottom nav
        page2.locator(".vtab").filter(has_text="Ruta").click()
        page2.wait_for_timeout(400)
        page2.screenshot(path=f"{OUT}/06_vendedor_ruta.png", full_page=False)
        print("✓ 06_vendedor_ruta.png")

        # 8. Tab KPIs
        page2.locator(".vtab").filter(has_text="KPIs").click()
        page2.wait_for_timeout(400)
        page2.screenshot(path=f"{OUT}/07_vendedor_kpis.png", full_page=False)
        print("✓ 07_vendedor_kpis.png")

        # 9. Tab Alertas vendedor
        page2.locator(".vtab").filter(has_text="Alertas").click()
        page2.wait_for_timeout(400)
        page2.screenshot(path=f"{OUT}/08_vendedor_alertas.png", full_page=False)
        print("✓ 08_vendedor_alertas.png")

        ctx2.close()
        browser.close()

    print("\n── Errores JS detectados ──")
    if errors:
        for e in errors:
            print(f"  {e}")
    else:
        print("  (sin errores)")

if __name__ == "__main__":
    run()
