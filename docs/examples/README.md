# Demo

## Before polydiff

```bash
$ git diff logo.png
Binary files a/logo.png and b/logo.png differ
```

## After polydiff

```bash
$ polydiff install
✓ polydiff configured successfully!

$ git diff logo.png
~ 92.2% similar
92.2% similar, 1 region(s) changed

Dimensions: 200x200 (unchanged)
File size: 634 bytes (unchanged)
Changed regions: 1
  Region 1: (60, 60) 81x81
```

## Standalone Usage

```bash
# Compare images
polydiff diff old.png new.png

# Compare PDFs
polydiff diff old.pdf new.pdf

# Compare Excel files
polydiff diff old.xlsx new.xlsx

# Generate HTML report
polydiff diff old.png new.png --format html --output report.html
```

## Screenshots

### Image Diff
![Image Diff Example](image_diff_example.png)

### PDF Diff
![PDF Diff Example](pdf_diff_example.png)

### Excel Diff
![Excel Diff Example](xlsx_diff_example.png)
