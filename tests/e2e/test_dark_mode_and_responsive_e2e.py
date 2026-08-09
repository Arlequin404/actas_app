import re
from pathlib import Path
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def luminance(rgb):
    values=[]
    for value in rgb:
        x=value/255
        values.append(x/12.92 if x <= .04045 else ((x+.055)/1.055)**2.4)
    return .2126*values[0]+.7152*values[1]+.0722*values[2]


def parse_rgb(value):
    nums = re.findall(r"[\d.]+", value)
    return tuple(int(float(x)) for x in nums[:3]) if len(nums) >= 3 else None


def contrast(fg,bg):
    l1,l2=sorted((luminance(fg),luminance(bg)),reverse=True)
    return (l1+.05)/(l2+.05)


def test_dark_mode_is_readable_across_main_interface(admin_page, urls, request):
    page=admin_page
    page.evaluate("localStorage.setItem('theme','dark')")
    pages=[("dashboard","/dashboard"),("create","/crear/actas"),("admin","/admin"),("builder","/admin/campos"),("companies","/admin/empresas"),("backup","/admin/respaldo")]
    for name,path in pages:
        page.goto(urls["web"]+path)
        expect(page.locator("html")).to_have_attribute("data-bs-theme","dark")
        controls=page.locator("input:visible, select:visible, textarea:visible, .card:visible, .modal-content:visible")
        for index in range(min(controls.count(),30)):
            element=controls.nth(index)
            styles=element.evaluate("""e=>{
              const s=getComputedStyle(e);
              let node=e, bg='rgb(0,0,0)';
              while(node){ const b=getComputedStyle(node).backgroundColor; if(!b.endsWith(', 0)') && b!=='rgba(0, 0, 0, 0)' && b!=='transparent'){bg=b;break;} node=node.parentElement; }
              return {c:s.color,b:bg,v:s.visibility,d:s.display,o:s.opacity};
            }""")
            assert styles["v"] != "hidden" and styles["d"] != "none" and float(styles["o"] or 1) > 0
            fg,bg=parse_rgb(styles["c"]),parse_rgb(styles["b"])
            if fg and bg:
                assert contrast(fg,bg) >= 2.5, f"Contraste bajo en {path}: {styles}"
        page.screenshot(path=f"test-artifacts/screenshots/dark-{name}.png", full_page=True)


def test_mobile_layout_has_no_major_horizontal_overflow(admin_page, urls):
    page=admin_page
    page.set_viewport_size({"width":390,"height":844})
    for path in ("/dashboard","/crear","/admin","/admin/campos"):
        page.goto(urls["web"]+path)
        overflow=page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
        assert overflow <= 12, f"Desbordamiento horizontal de {overflow}px en {path}"
