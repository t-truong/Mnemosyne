# Mnemosyne :lock_with_ink_pen:
Harness the power of the Goddess of Memory

Contains:

- Long term storage utility
  - ./writeArchive.zsh: Script to write to storage
    - Checksum -> Compress -> Encrypt -> Copy to storage
    - *Only* encrypted data and checksum is copied to storage; raw data never exists in storage
  - ./readArchive.zsh: Script to read from storage
    - Copy to local -> Decrypt -> Decompress -> Checksum
    - *Only* decrypt locally; raw data never exists in storage

- **Apple**: Data extraction utilities for Apple products
  - ./Apple/exportMessages.py: Pulls data from Messages app
    - Export text messages to a .txt file
    - Export message attachments
