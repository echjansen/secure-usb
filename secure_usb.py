import os
import logging
from rich.console import Console
from rich.rule import Rule
from rich.prompt import Prompt
from rich.theme import Theme

from lib.shell import Shell
from lib.system import System
from lib.userentry import UserEntry

# Python constants
DEBUG = True

if __name__ == "__main__":

#-- Environment Variables  ----------------------------------------------------

    # Create environment variables.
    os.environ["DEVICE"] = ""
    os.environ["DEVICE_NAME"] = ""
    os.environ["DEVICE_WIPE"] = ""
    os.environ["USER_NAME"] = ""
    os.environ["USER_PASS"] = ""
    os.environ["PART1"] = ""
    os.environ["PART2"] = ""
    os.environ["PART3"] = ""
    os.environ["PART4"] = ""
    os.environ["PART1_UUID"] = ""
    os.environ["PART2_UUID"] = ""
    os.environ["PART3_UUID"] = ""
    os.environ["PART4_UUID"] = ""
    os.environ["SYSTEM_LOCALE"] = ""
    os.environ["SYSTEM_KEYB"] = ""
    os.environ["SYSTEM_TIMEZONE"] = ""

    # set environment variables 'constants'
    os.environ['PART1_LABEL']  = "README"
    os.environ['PART2_LABEL']  = "EFI"
    os.environ['PART3_LABEL']  = "LINUX"
    os.environ['PART4_LABEL']  = "STORAGE"
    os.environ['PART4_FORMAT'] = "BTRFS"
    os.environ['LINUX_ENV']    = "LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 KEYMAP=us DEBIAN_FRONTEND=noninteractive TERM=xterm-color"
    os.environ['LINUX_PKGS']   = "linux-image-amd64 firmware-linux firmware-iwlwifi zstd grub-efi cryptsetup cryptsetup-initramfs btrfs-progs fdisk gdisk sudo network-manager xserver-xorg xinit lightdm xfce4 dbus-x11 thunar xfce4-terminal firefox-esr keepassxc network-manager-gnome mg"


#-- Update System  ------------------------------------------------------------

    system = System(debug=DEBUG)
    system.check_sudo()
    #TODO system.check_pacman(['dialog', 'python-rich', 'debootstrap', 'gptfdisk'])

#-- Create Objects ------------------------------------------------------------

    userentry = UserEntry()
    theme     = Theme(Shell.COLOR_THEME)
    console   = Console(theme=theme)
    prompt    = Prompt(console=console)
    log       = logging.getLogger("shell")
    shell     = Shell(console=console, log=log, debug=DEBUG)

#-- System Check --------------------------------------------------------------

    console.clear()

#-- User input ----------------------------------------------------------------

    # Get user variables
    if not os.environ.get('DEVICE'):          os.environ['DEVICE']          = userentry.configure_drive()
    if not os.environ.get('DEVICE_NAME'):     os.environ['DEVICE_NAME']     = userentry.configure_hostname('Secure-USB').lower()
    if not os.environ.get('DEVICE_WIPE'):     os.environ['DEVICE_WIPE']     = userentry.run_yesno_str("Hard drive", "Wipe the entire drive (lengthy)")
    if not os.environ.get('USER_NAME'):       os.environ['USER_NAME']       = userentry.configure_username()
    if not os.environ.get('USER_PASS'):       os.environ['USER_PASS']       = userentry.configure_userpassword()
    if not os.environ.get('SYSTEM_LOCALE'):   os.environ['SYSTEM_LOCALE']   = userentry.configure_locale()
    if not os.environ.get('SYSTEM_KEYB'):     os.environ['SYSTEM_KEYB']     = userentry.configure_keyboard()
    if not os.environ.get('SYSTEM_TIMEZONE'): os.environ['SYSTEM_TIMEZONE'] = userentry.configure_timezone()

#-- User validation -----------------------------------------------------------
    console.print(Rule("Installation selections"), style='success')

    if os.environ.get('DEVICE'):
        console.print(f'Selected drive:.... [green]{os.environ.get('DEVICE')}[/]', style='info')
    else:
        console.print('No drive selected.', style='critical')

    if os.environ.get('DEVICE_WIPE'):
        console.print(f'Wipe drive:........ [green]{os.environ.get('DEVICE_WIPE')}[/]', style='info')
    else:
        os.environ['DEVICE_WIPE'] = 'no'

    if os.environ.get('DEVICE_NAME'):
        console.print(f'Device name:....... [green]{os.environ.get('DEVICE_NAME')}[/]', style='info')
    else:
        os.environ['DEVICE_NAME'] = "Secure-USB".lower()

    if os.environ.get('USER_NAME'):
        console.print(f'User name:......... [green]{os.environ.get('USER_NAME')}[/]', style='info')
    else:
        console.print('No user name selected.', style='critical')

    if os.environ.get('SYSTEM_LOCALE'):
        console.print(f'System locale:..... [green]{os.environ.get('SYSTEM_LOCALE')}[/]', style='info')
    else:
        console.print('No system locale selected.', style='critical')

    if os.environ.get('SYSTEM_KEYB'):
        console.print(f'System keyboard:... [green]{os.environ.get('SYSTEM_KEYB')}[/]', style='info')
    else:
        console.print('No system keyboard selected.', style='critical')

    if os.environ.get('SYSTEM_TIMEZONE'):
        console.print(f'System timezone:... [green]{os.environ.get('SYSTEM_TIMEZONE')}[/]', style='info')
    else:
        console.print('No system timezone selected.', style='critical')

    if prompt.ask('\nAre these selections correct, and continue installation?', choices=['y', 'n']) == 'n':
        exit()

#-- Partitioning --------------------------------------------------------------
    console.print(Rule("Partitioning USB Device"), style='success')

    #--------------------------------------------------------------------------
    # Create Partitions
    #--------------------------------------------------------------------------
    # - Partition 1: FAT32 partition which contains a README.txt with contact details in case the USB key is lost
    # - Partition 2: EFI partition with Microsoft signed bootloader (to access your data from any physical computer you have access to)
    # - Partition 3: LUKS encrypted partition which contains a minimal Linux install to access your data from any computer
    # - Partition 4: LUKS encrypted partition which will contain all your data
    #--------------------------------------------------------------------------

    # Write random data to the whole disk
    if os.environ.get('DEVICE_WIPE') == 'yes': shell.execute('Disk - Write random data to disk', 'dd bs=1M if=/dev/urandom of={DEVICE}', check_returncode=False)

    # Remove any file system magic bytes
    shell.execute('Disk - Remove file magic bytes','wipefs --all {DEVICE}')

    # Create partition table
    # command = "sgdisk --clear /dev/sdb --new 1::+64MiB --new 2::+128MiB --typecode 2:ef00 /dev/sdb --new 3::+10GiB --new 4::0"
    shell.execute('Partitioning - Create partition table', 'sgdisk --clear {DEVICE} --new 1::+64MiB --new 2::+128MiB --typecode 2:ef00 {DEVICE} --new 3::+10GiB --new 4::0')

    # Rename the partitions
    # command = "sgdisk /dev/sdb --change-name=1:README --change-name=2:EFI --change-name=3:LINUX_ENCRYPTED --change-name=4:STORAGE_ENCRYPTED"
    shell.execute('Partitioning - Name the partitions', 'sgdisk {DEVICE} --change-name=1:{PART1_LABEL} --change-name=2:{PART2_LABEL} --change-name=3:{PART3_LABEL} --change-name=4:{PART4_LABEL}')

    # Get the partitions (/dev/sda1 etc)
    os.environ['PART1'] = system.get_partition(os.environ.get('DEVICE'), 1)
    os.environ['PART2'] = system.get_partition(os.environ.get('DEVICE'), 2)
    os.environ['PART3'] = system.get_partition(os.environ.get('DEVICE'), 3)
    os.environ['PART4'] = system.get_partition(os.environ.get('DEVICE'), 4)

    # -- partition 1 - README -------------------------------------------------
    shell.execute('Partition 1 - Formatting {PART1_LABEL}','mkfs.vfat -n {PART1_LABEL} -F 32 {PART1}')
    shell.execute('Partition 1 - Get UUID for {PART1_LABEL}', 'lsblk -o uuid {PART1} | tail -1', output_var='PART1_UUID')

    # -- partition 2 - EFI ----------------------------------------------------
    shell.execute('Partition 2 - Formatting {PART2_LABEL}','mkfs.vfat -n {PART2_LABEL} -F 32 {PART2}')
    shell.execute('Partition 2 - Get UUID for {PART2_LABEL}', 'lsblk -o uuid {PART2} | tail -1', output_var='PART2_UUID')

    # -- partition 3 ----------------------------------------------------------
    shell.execute('Partition 3 - Encrypting {PART3_LABEL}','cryptsetup luksFormat -q --type luks1 --label {PART3_LABEL} {PART3}',input="{USER_PASS}")
    shell.execute('Partition 3 - Get UUID for {PART3_LABEL}', 'cryptsetup luksUUID {PART3}', output_var='PART3_UUID')
    shell.execute('Partition 3 - Open {PART3_LABEL}', 'cryptsetup luksOpen {PART3} {PART3_UUID}' ,input="{USER_PASS}")
    shell.execute('Partition 3 - Set file system {PART3_LABEL} to ext4', 'mkfs.ext4 -L {PART3_LABEL} /dev/mapper/{PART3_UUID}')

    # -- partition 4 ----------------------------------------------------------
    shell.execute('Partition 4 - Encrypting {PART4_LABEL}','cryptsetup luksFormat -q --type luks1 --label {PART4_LABEL} {PART4}',input="{USER_PASS}")
    shell.execute('Partition 4 - Get UUID for {PART4_LABEL}', 'cryptsetup luksUUID {PART4}', output_var='PART4_UUID')
    shell.execute('Partition 4 - Open {PART4_LABEL}', 'cryptsetup luksOpen {PART4} {PART4_UUID}' ,input="{USER_PASS}")

    if os.environ.get('PART4_FORMAT') == "BTRFS":
        shell.execute('Partition 4 - Set file system {PART4_LABEL} to BTRFS', 'mkfs.btrfs --label {PART4_LABEL} /dev/mapper/{PART4_UUID}')
        shell.execute('Partition 4 - Mount {PART4_LABEL}', 'mount /dev/mapper/{PART4_UUID} /mnt')
        shell.execute('Partition 4 - Create subvolume @snapshots' , 'btrfs subvolume create /mnt/@snapshots')
        shell.execute('Partition 4 - Umount {PART4_LABEL}', 'umount /mnt')
    else:
        shell.execute('Partition 4 - Set file system {PART4_LABEL} to EXT4', 'mkfs.ext4 -L {PART4_LABEL} /dev/mapper/{PART4_UUID}')

#-- Install Readme  ------------------------------------------------------------
    console.print(Rule("Installing Readme"), style='success')

    shell.execute('Partition 1 - Mount {PART1_LABEL}','mount {PART1} /mnt')
    shell.execute('Partition 1 - Copy readme.org', 'cp README.org /mnt/README.org')
    shell.execute('Partition 1 - Umount', 'umount /mnt')

#-- Install Linux  ------------------------------------------------------------
    console.print(Rule("Installing Linux"), style='success')

    #--------------------------------------------------------------------------
    # Install Linux on the embedded USB device
    #--------------------------------------------------------------------------
    # We want it to :
    #
    # - Be bootable on any secure boot enabled computer
    # - Auto-mount the storage partition
    #
    # Debian has been chosen for two reasons:
    #
    # - Because it's very stable, if we have to boot into this USB device it probably means something went wrong at some point and we don't want to deal with a broken install
    # - Because it supports secure boot out of the box, meaning we will be able to boot into it on any computer (as long as it allows us to boot into external USB)
    #--------------------------------------------------------------------------

    # Mount linux partition
    shell.execute('Partition 3 - Mount {PART3_LABEL}', 'mount /dev/mapper/{PART3_UUID} /mnt')

    # Install Debian (add the --foreign option if the host is different from the target)
    shell.execute('Linux - Install Linux Debian', 'debootstrap --arch amd64 --components main,contrib,non-free-firmware stable /mnt http://ftp.us.debian.org/debian')

    # Mount resources
    shell.execute('Linux - Mount "boot/efi"', 'mount --mkdir {PART2} /mnt/boot/efi')
    shell.execute('Linux - Mount "proc"',     'mount -t proc  proc /mnt/proc')
    shell.execute('Linux - Mount "sys"',      'mount -t sysfs sys  /mnt/sys')
    shell.execute('Linux - Mount "dev"',      'mount -o bind  /dev /mnt/dev')
    shell.execute('Linux - Mount "efivars"',  'mount --rbind /sys/firmware/efi/efivars /mnt/sys/firmware/efi/efivars')

    # Configure Linux
    shell.execute('Linux - Set hostname',   'echo {DEVICE_NAME} | tee /mnt/etc/hostname')
    shell.execute('Linux - Set hosts',      'echo "127.0.0.1 {DEVICE_NAME}" | tee -a /mnt/etc/hosts')
    shell.execute('Linux - Set motd',       'echo | tee /mnt/etc/motd')
    shell.execute('Linux - Set repository', 'echo "deb http://security.debian.org/ stable-security main contrib non-free-firmware" | tee -a /mnt/etc/apt/sources.list')

    # shell.execute('Set the system font to "$SYSTEM_FONT"', 'echo "FONT=$SYSTEM_FONT" >/mnt/etc/vconsole.conf')
    # shell.execute('Set the hostname to $SYSTEM_HOSTNAME', 'echo "$SYSTEM_HOSTNAME" >/mnt/etc/hostname')

    shell.execute('Set the system keyboard to {SYSTEM_KEYB}"', 'echo "KEYMAP={SYSTEM_KEYB}" >>/mnt/etc/vconsole.conf')
    shell.execute('Set the language to {SYSTEM_LOCALE}', 'echo "{SYSTEM_LOCALE}" >>/mnt/etc/locale.gen')
    shell.execute('Set the timezone to {SYSTEM_TIMEZONE}', 'ln -sf /usr/share/zoneinfo/{SYSTEM_TIMEZONE} /mnt/etc/localtime')
    shell.execute('Generate locale', '{LINUX_ENV} chroot /mnt bash --login -c "locale-gen"')

    # Update Linux repositories
    shell.execute('Linux - Update repositories', '{LINUX_ENV} chroot /mnt bash --login -c "apt-get update && apt-get upgrade -y"')

    # Install packages
    shell.execute('Linux - Install packages', '{LINUX_ENV} chroot /mnt bash --login -c "apt-get install -y {LINUX_PKGS}"')

    # Create swapfile
    shell.execute('Linux - Allocate swapfile', 'fallocate -l 1G /mnt/swapfile')
    shell.execute('Linux - Set permissions swapfile', 'chmod 600 /mnt/swapfile')
    shell.execute('Linux - Make swapfile', 'mkswap /mnt/swapfile')

    # Create keyfiles for to auto-mount partitions
    shell.execute('Linux - Create Keyfile for {PART3_LABEL}', 'dd bs=512 count=4 if=/dev/random of=/mnt/root/luks_{PART3_UUID}.keyfile iflag=fullblock')
    shell.execute('Linux - Set permission Keyfile {PART3_LABEL}', 'chmod 400 /mnt/root/luks_{PART3_UUID}.keyfile')
    shell.execute('Linux - Create Keyfile for {PART4_LABEL}', 'dd bs=512 count=4 if=/dev/random of=/mnt/root/luks_{PART4_UUID}.keyfile iflag=fullblock')
    shell.execute('Linux - Set permission Keyfile {PART4_LABEL}', 'chmod 400 /mnt/root/luks_{PART4_UUID}.keyfile')

    # Enroll the keyfiles so we can open the USB device
    shell.execute('Linux - Enroll Keyfile for (PART3_LABEL)', 'cryptsetup luksAddKey {PART3} /mnt/root/luks_{PART3_UUID}.keyfile', input="{USER_PASS}")
    shell.execute('Linux - Enroll Keyfile for (PART4_LABEL)', 'cryptsetup luksAddKey {PART4} /mnt/root/luks_{PART4_UUID}.keyfile', input="{USER_PASS}")

    # And add the following to crypttab so that `cryptsetup-initramfs` knows which key to use to allow the initramfs to decrypt the root partition:
    shell.execute('Linux - Configure crypttab for {PART3_LABEL}', 'echo "{PART3_UUID} UUID={PART3_UUID} /root/luks_{PART3_UUID}.keyfile luks,discard" | tee -a /mnt/etc/crypttab')
    shell.execute('Linux - Configure crypttab for {PART4_LABEL}', 'echo "{PART4_UUID} UUID={PART4_UUID} /root/luks_{PART4_UUID}.keyfile luks,discard" | tee -a /mnt/etc/crypttab')
    shell.execute('Linux - Configure cryptsetup hook', 'echo KEYFILE_PATTERN="/root/luks_*.keyfile" | tee -a /mnt/etc/cryptsetup-initramfs/conf-hook')

    # Setup fstab
    shell.execute('Linux - Configure fstab for {PART2_LABEL}', 'echo "UUID={PART2_UUID} /boot/efi vfat rw,relatime,fmask=0077,dmask=0077,codepage=437,iocharset=ascii,shortname=mixed,utf8,errors=remount-ro 0 0" | tee -a /mnt/etc/fstab')
    shell.execute('Linux - Configure fstab for {PART3_LABEL}', 'echo "/dev/mapper/{PART3_UUID} / ext4 defaults 0 1" | tee /mnt/etc/fstab')
    shell.execute('Linux - Configure fstab for {PART4_LABEL}', 'echo "/dev/mapper/{PART4_UUID} /storage btrfs defaults,noatime,nodiratime,subvol=@snapshots,compress=zstd,space_cache=v2    0  2" | tee -a /mnt/etc/fstab')
    shell.execute('Linux - Configure fstab for swapfile', 'echo "/swapfile none swap sw 0 0" | tee -a /mnt/etc/fstab')

    # Setup bootloader
    shell.execute('Linux - Configure grub', 'echo GRUB_ENABLE_CRYPTODISK=y | tee -a /mnt/etc/default/grub')
    shell.execute('Linux - Configure grub', 'echo GRUB_CMDLINE_LINUX="cryptdevice=UUID={PART3_UUID}:{PART3_UUID}" | tee -a /mnt/etc/default/grub')
    shell.execute('Linux - Configure grub', 'echo GRUB_DISTRIBUTOR="{DEVICE_NAME}" | tee -a /mnt/etc/default/grub')
    shell.execute('Linux - Configure intitamfs', 'echo UMASK=0077 | tee -a /mnt/etc/initramfs-tools/initramfs.conf')
    shell.execute('Linux - Update initramfs', 'chroot /mnt bash --login -c "update-initramfs -u -k all"')
    shell.execute('Linux - Update grub', 'chroot /mnt bash --login -c "update-grub"')
    shell.execute('Linux - Install grub', 'chroot /mnt bash --login -c "grub-install {DEVICE}"')

    # Create user
    shell.execute('Linux - Create user {USER_NAME}',  'chroot /mnt bash --login -c "useradd -m {USER_NAME} -s /bin/bash"')
    shell.execute('Linux - Set password {USER_NAME}', 'chroot /mnt bash --login -c "chpasswd"', input='{USER_NAME}:{USER_PASS}\n')
    shell.execute('Linux - Add sudo to {USER_NAME}',  'chroot /mnt bash --login -c "usermod -aG sudo {USER_NAME}"')

    # Allow user access to storage
    shell.execute('Linux - Create storage directory', 'mkdir /mnt/storage')
    shell.execute('Linux - Mount storage', 'mount /dev/mapper/{PART4_UUID} /mnt/storage')
    shell.execute('Linux - Set permissions for storage', 'chown -R 1000:1000 /mnt/storage')

    # Auto login the user
    shell.execute('Linux - Auto login {USER_NAME}', 'sed -i "s/#autologin-user=/autologin-user={USER_NAME}/g" /mnt/etc/lightdm/lightdm.conf')

    # Set reminder in bashrc for user
    shell.execute('Linux - Reminder for {USER_NAME}', 'echo "echo Storage partition is mounted at /storage ;)" | tee -a /mnt/home/{USER_NAME}/.bashrc')

    # Start Services
    shell.execute('Linux - Start Network Manager', 'chroot /mnt bash --login -c "systemctl enable NetworkManager"')

    # -- Cleanup ---
    shell.execute('Partitions  - Umount', 'umount --recursive /mnt')
    shell.execute('Partition 4 - Close {PART4_LABEL}', 'cryptsetup luksClose {PART4_UUID}')
    shell.execute('Partition 3 - Close {PART3_LABEL}', 'cryptsetup luksClose {PART3_UUID}')
    # -- Cleanup ---

    console.print(Rule("Done"))
