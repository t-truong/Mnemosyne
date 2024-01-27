#!/bin/zsh
####################################################################################################
# readArchive.zsh
# by (github.com/t-truong)
# Read files from storage
#
# Dependencies are {sha256sum, gpg}
# ${@[1,-1]}= Source to read from archive (has be a directory containing both *.tar.gz.gpg and *.sha256sum)
#
# 1) Copy from storage to current directory
# 2) Decrypt tarball
# 3) Decompress tarball
# 4) Verify checksum
# 5) Delete local tarball and checksum files
####################################################################################################





autoload colors && colors
#Initialization-------------------------------------------------------------------------------------
Paths_Source=("${@[1,-1]}")
for p in $Paths_Source; do
    b=$(basename $p)
    if [[ ! -d "$p" ]]; then
        echo "$fg[red]Error:$reset_color Archive source {$p} given is not a directory or does not exist"
        exit 1
    elif [[ ! -f "$p/$b.tar.gz.gpg" ]]; then
        echo "$fg[red]Error:$reset_color Encrypted archive file {$p/$b.tar.gz.gpg} not found"
        exit 1
    elif [[ ! -f "$p/$b.sha256sum" ]]; then
        echo "$fg[red]Error:$reset_color Checksum file {$p/$b.sha256sum} not found"
        exit 1
    fi
done

echo "Will read these from archive: {$fg[cyan]$Paths_Source$reset_color}"
for p in $Paths_Source; do
    if [[ -d "./$(basename $p)" ]]; then
        echo "$fg[yellow]Warning:$reset_color Local directory {./$(basename $p)} already exists, will overwrite files inside"
    fi
done
read -q "confirm?Begin read process? [y/N]: " && [[ "$confirm" == [yY] ]] && echo "" || exit 0
read -s "Password?Password: " && echo ""
read -s "x?Confirm Password: " && echo ""
if [[ "$Password" != "$x" ]]; then echo "$fg[red]Error:$reset_color Confirmation password does not match"; exit 1; fi
unset x
echo ""
#Archive Process------------------------------------------------------------------------------------
for source in $Paths_Source; do
    b=$(basename $source)
    destination="./$b"
    mkdir -p "$destination"
    echo "Reading {$fg[cyan]$source$reset_color}"
    #Copy from storage------------------------------------------------------------------------------
    cp "$source/$b.tar.gz.gpg" "$source/$b.sha256sum" "$destination"
    echo "    Archive copied from storage"
    #Decrypt tarball--------------------------------------------------------------------------------
    gpg --no-symkey-cache --quiet -o "$destination/$b.tar.gz" --batch --passphrase "$Password" --decrypt "$destination/$b.tar.gz.gpg"
    echo "    Decryption completed"
    #Decompress tarball-----------------------------------------------------------------------------
    tar -xzf "$destination/$b.tar.gz" > /dev/null 2>&1
    echo "    Decompression completed"
    #Verify checksum--------------------------------------------------------------------------------
    code=$(sha256sum --check --status "$destination/$b.sha256sum")
    if [[ "$code" -eq 0 ]]; then
        echo "    Checksum verified"
    else
        echo "    $fg[red]Error:$reset_color Checksum does not match"
        exit 1
    fi
    #Clean up---------------------------------------------------------------------------------------
    rm -f "$destination/$b.tar.gz.gpg"
    rm -f "$destination/$b.tar.gz"
    rm -f "$destination/$b.sha256sum"
done
#Exit-----------------------------------------------------------------------------------------------





####################################################################################################
# writeArchive.zsh
# by (github.com/t-truong)
# Writes files to storage medium
####################################################################################################
