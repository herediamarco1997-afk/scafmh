"""Convert PDF acta to JPG for visual comparison."""
import fitz
doc = fitz.open('D:\\sistema de af\\sistema_activos\\test_acta.pdf')
npages = len(doc)
print('Pages: %d' % npages)
page = doc[0]
pix = page.get_pixmap(dpi=200)
pix.save('D:\\sistema de af\\sistema_activos\\acta_pag1.jpg')
print('Page 1 saved')
if npages > 1:
    page2 = doc[1]
    pix2 = page2.get_pixmap(dpi=200)
    pix2.save('D:\\sistema de af\\sistema_activos\\acta_pag2.jpg')
    print('Page 2 saved')
doc.close()
