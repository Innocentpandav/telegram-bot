{ pkgs }: {
  deps = [
    pkgs.python312Full   # use Python 3.12 to match Replit default
    pkgs.tesseract       # install Tesseract OCR
    pkgs.git             # sometimes useful for pulling updates
  ];
}
