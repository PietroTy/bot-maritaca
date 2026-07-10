import time
from modules.exporter import _gerar_pdf, _gerar_docx, _gerar_txt

secoes = [{"titulo": "Teste", "texto": "A " * 50000}]  # 50,000 words
t0 = time.time()
print("Txt...")
_gerar_txt(secoes, "Tema", "pt-br")
t1 = time.time()
print("Docx...")
_gerar_docx(secoes, "Tema", "pt-br")
t2 = time.time()
print("PDF...")
try:
    import signal
    def handler(signum, frame):
        raise TimeoutError("PDF timeout")
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(5)
    _gerar_pdf(secoes, "Tema", "pt-br")
    signal.alarm(0)
    print("PDF DONE")
except Exception as e:
    print(f"PDF FAILED: {e}")
t3 = time.time()

print(f"TXT: {t1-t0}s | DOCX: {t2-t1}s | PDF: {t3-t2}s")
