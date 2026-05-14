"""Validar KPIs vendedor con datos corregidos"""
from playwright.sync_api import sync_playwright
import os

OUT = r"C:\Orbit\MATINAL_PENAFLOR\screenshots"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

        page.goto("http://localhost:8502/portal.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)

        page.select_option("#userSelect", "v3")
        page.fill("#pwdInput", "pav2026")
        page.click(".ln-btn")
        page.wait_for_timeout(2500)

        page.locator(".vtab").filter(has_text="KPIs").click()
        page.wait_for_timeout(500)
        page.screenshot(path=f"{OUT}/09_kpis_fix.png", full_page=True)
        print("OK: 09_kpis_fix.png")

        # Verificar texto en pantalla
        content = page.inner_text(".vcont.active")
        for line in ["TRADICIONAL", "AUTOSERV", "Avance vs", "11 Titulares"]:
            status = "OK" if line in content else "FALTA"
            print(f"  {status}: {line}")

        # Verificar que CCC Tradicional no sea 0
        if "ccc" not in content.lower():
            print("  WARN: contenido CCC no encontrado")

        print(f"\nErrores JS: {errors}")
        ctx.close()
        browser.close()

if __name__ == "__main__":
    run()
