#!/bin/zsh
####################################################################################################
# writeArchive.zsh
# by (github.com/t-truong)
# Writes files to storage medium
#
# Dependencies are {sha256sum}
# ${@[1]}   = Path to archive directory (can be local directory or mounted disk)
# ${@[2,-1]}= Targets to archive (has to be directories; if user wants to archive a single file, move into directory)
#
# 1) Create checksum file to check integrity on future reads
# 2) Compress to tarball
# 3) Encrypt tarball
# 4) Move to storage
# 5) Ask user to delete original files
####################################################################################################





autoload colors && colors
#Initialization-------------------------------------------------------------------------------------
Path_Archive="$1"
Paths_Target=("${@[2,-1]}")
if [[ ! -d "$Path_Archive" ]]; then echo "$fg[red]Error:$reset_color Archive location {$Path_Archive} given is not a directory"; exit 1; fi
for p in $Paths_Target; do
    if [[ ! -d "$p" ]]; then echo "$fg[red]Error:$reset_color Archive target {$p} is not a directory"; exit 1; fi
done

echo "Will write to archive at {$fg[cyan]$Path_Archive$reset_color}"
echo "Will archive these directories: {$fg[cyan]$Paths_Target$reset_color}"
read -q "confirm?Begin archival process? [y/N]: " && [[ "$confirm" == [yY] ]] && echo "\n" || exit 0
#Archive Process------------------------------------------------------------------------------------
for target in $Paths_Target; do
    echo "Archiving {$fg[cyan]$target$reset_color}"
    #Checksum---------------------------------------------------------------------------------------
    checksums=$(find "$target" -type f -exec sha256sum {} \;)                             #raw checksums
    modded=$(awk '{ printf("%s %d %s\n", $1, gsub(/\//,"/", $2), $2) }' <<< "$checksums") #insert path depth
    sorted=$(sort -V --key=2.2 <<< "$modded" | awk '{ printf("%s %s\n", $1, $3) }')       #sort by path depth and path then remove path depth
    echo "$sorted" > "$target.sha256sum"
    echo "    Checksum completed"
    #Tarball----------------------------------------------------------------------------------------
    #tried to tarball then pipe into gpg but could not get it to work because error with tar
    #"wrote only 4096 of 10240 bytes"
    tar -czf "$target.tar.gz" "$target" > /dev/null 2>&1
    echo "    Compression completed"
    #Encrypt tarball--------------------------------------------------------------------------------
    gpg --s2k-digest-algo SHA512 --s2k-mode 3 --s2k-count 1048576 --s2k-cipher-algo AES256\
        -o "$target.tar.gz.gpg" --symmetric "$target.tar.gz"
    rm -f "$target.tar.gz"
    echo "    Encryption completed"
    #Move to storage--------------------------------------------------------------------------------
    mv "$target.sha256sum" "$target.tar.gz.gpg" "$Path_Archive"
    echo "    Data moved to storage"
done
echo ""
#Exit-----------------------------------------------------------------------------------------------
echo "Original data locations: {$fg[cyan]$Paths_Target$reset_color}"
read -q "confirm?Delete original data? [y/N]: "
if [[ "$confirm" == [yY] ]]; then
    :
else
    echo "\nExiting..."
    exit 0
fi
rm -rf "${Paths_Target[@]}" #$Paths_Target is an array, must access all elements at once to use as string for deletion
echo "\nOriginal data deleted\nExiting..."





####################################################################################################
# writeArchive.zsh
# by (github.com/t-truong)
# Writes files to storage medium
####################################################################################################
