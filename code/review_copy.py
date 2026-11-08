"""Make e-mail-sized copies of the Word deliverables (figures as 1700 px JPEG)."""
import zipfile, io, sys
from PIL import Image


def jpeg_copy(src, dst, px=1700, q=82):
    zi = zipfile.ZipFile(src); zo = zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
    ren = {it.filename: it.filename[:-4] + ".jpeg" for it in zi.infolist() if it.filename.startswith("word/media/") and it.filename.lower().endswith(".png")}
    for it in zi.infolist():
        b = zi.read(it.filename); name = it.filename
        if name in ren:
            im = Image.open(io.BytesIO(b)).convert("RGB"); im.thumbnail((px, px)); o = io.BytesIO(); im.save(o, "JPEG", quality=q, optimize=True); b = o.getvalue(); name = ren[name]
        elif name.endswith(".rels"):
            t = b.decode()
            for k, v in ren.items():
                t = t.replace(k.split("word/")[1], v.split("word/")[1])
            b = t.encode()
        elif name == "[Content_Types].xml":
            t = b.decode()
            if 'Extension="jpeg"' not in t:
                t = t.replace("<Default ", '<Default Extension="jpeg" ContentType="image/jpeg"/><Default ', 1)
            b = t.encode()
        zo.writestr(name, b)
    zo.close()


if __name__ == "__main__":
    base = "/home/bongani/PhD_Thesis/UCT PHD 2026/Chapter 2 Literature Review"
    v2 = f"{base}/Bibliometry Analysis/v2_2026-10"
    jpeg_copy(f"{v2}/manuscript/Geospatial_Proxy_Bibliometric_Review_DRAFT.docx", f"{v2}/manuscript/Geospatial_Proxy_Bibliometric_Review_REVIEW_COPY.docx")
    jpeg_copy(f"{v2}/manuscript/Supplementary_Figures.docx", f"{v2}/manuscript/Supplementary_Figures_REVIEW_COPY.docx")
    jpeg_copy(f"{base}/Chapter_2_Literature_Review_and_Bibliometric_Analysis_INTEGRATED.docx", f"{v2}/thesis/Chapter_2_REVIEW_COPY.docx")
    print("review copies written")
