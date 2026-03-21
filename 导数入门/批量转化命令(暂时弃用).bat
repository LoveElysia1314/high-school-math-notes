for %f in (md/*.md) do pandoc "md/%f" -o "docx/%~nf.docx"
for %f in (md/*.md) do pandoc "md/%f" -o "tex/%~nf.tex"
for %f in (md/*.md) do pandoc "md/%f" -o "html/%~nf.html"