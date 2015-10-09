#!/usr/bin/perl -Tw

use strict;
use CGI;
use Fcntl ':flock';
use Digest::MD5;

use constant SUPPORTED_FILETYPES  => qw(jpg png gif);
use constant MAXIMUM_FILESIZE     => 2048;			#(in kB)
use constant THUMBNAIL_QUALITY    => 100;
use constant DIR				  => 'images';
use constant ADMIN_PASSWORD       => 'CHANGEME';
use constant CRYPTOGRAPHIC_SECRET => 'CHANGEME';
use constant PRUNING_NUMBER		  => 0;				#delete oldest image when at this image total (0 = disable)
use constant PRUNING_SIZE		  => 100 * 1024;	#delete oldest image when at this total filesize (in kB) (0 = disable)

my $index = DIR . '/' . $ENV{SCRIPT_NAME};
$index =~ s/\/[^\/]*$/\//;
abort('This file is not placed in a board folder.') if !(-e 'res');
abort('This software is using the default security settings')
  if ADMIN_PASSWORD       eq 'CHANGEME'
  or CRYPTOGRAPHIC_SECRET eq 'CHANGEME';
  
unless (-d DIR){
	mkdir(DIR, 0755);
	open my $htaccess, '>>', DIR . '/.htaccess' or die "Failed to generate .htaccess file.";
	print $htaccess "DirectoryIndex index.html\nAddCharset utf-8 html\n\n<Files uploads.txt>\nDeny from all\n</Files>\n\n<IfModule mod_rewrite.c>\nRewriteEngine On\nRewriteRule ^([0-9]+)/.*" . '\.(.*)$ src/$1.$2' . "\n</IfModule>\n";
	close $htaccess;
}

my $req = new CGI;
if ($ENV{'REQUEST_METHOD'} eq 'POST') {
    my $time = time;
    my $ip = encode_base64(RC4(CRYPTOGRAPHIC_SECRET, $ENV{REMOTE_ADDR}));
    my $upload = $req->param('upload');
    my ($filename, $size, $extension, $width, $height) = analyze_image($upload);
    my $hash  = upload_image($time, $extension, $upload);
    my $abort = verify_image($hash, $time, $ip, $filename, $extension, $size, $width, $height);
    if ($abort) {
        unlink DIR . '/src/' . $time . '.' . $extension;
        abort($abort); }
    my $id = add_entry($hash, $time, $ip, $filename, $extension, $size, $width, $height);
    rename DIR . "/src/$time.$extension", DIR . "/src/$id.$extension" or abort('Could not edit the image file');
    make_thumbnail($id, $extension, $width, $height) if $width;
	pruning();
    build_pages($index);
    redirect($index); }
elsif ($ENV{'QUERY_STRING'}) {
    my $ip = encode_base64(RC4(CRYPTOGRAPHIC_SECRET, $ENV{REMOTE_ADDR}));
    my $id = $req->param('file');
    my $admin = $req->param('admin');
    my $confirm = $req->param('confirm');
    abort('Invalid upload number') unless $id =~ /^[0-9]+$/;
    open my $database, '<', DIR . '/uploads.txt';
    flock $database, LOCK_SH;
    while (<$database>) {
        /^([^\s]+) ([^\s]+) ([^\s]+) ([^\s]+) /;
        my ($db_id, $db_ip) = ($1, $4);
        if ($id eq $db_id) {
            our $user_match = 1 if $ip eq $db_ip;
            our $user_match = 1 if $admin eq ADMIN_PASSWORD;
            last; }}
    close $database;
    abort('You did not upload this file') unless $main::user_match;
    if ($confirm) {
        delete_upload($id);
        build_pages($index);
        redirect($index); }
    else {
        print_delete_page($index, $id, $admin);
        exit; }}
else {
    mkdir(DIR . '/src/', 0755)   unless -d DIR . '/src/';
    mkdir(DIR . '/thumb/', 0755) unless -d DIR . '/thumb/';
    build_pages($index);
    redirect($index); }

# Subroutines

sub upload_image($$$) {
    my ($filename, $extension, $upload) = @_;
    my ($safe_filename) = $filename =~ /^([0-9]+)$/;
    if (!$safe_filename) { abort('Invalid file'); }
    open OUTFILE, '>', DIR . '/src/' . $safe_filename . '.' . $extension;
    binmode OUTFILE;
    my $md5 = Digest::MD5->new;
    while (<$upload>) {
        print OUTFILE;
        $md5->add($_); }
    close OUTFILE;
    return $md5->hexdigest; }

sub make_thumbnail($$$$) {
    my ($filename, $extension, $width, $height) = @_;
    my $source_file  = DIR . '/src/' . $filename . '.' . $extension;
    my $thumbnail = DIR . '/thumb/' . $filename . '.jpg';
    $source_file .= "[0]" if ($extension =~ /^(gif)$/);
    my ($tn_width, $tn_height);
    if ($width <= 200 and $height <= 200) {
        $tn_width  = $width;
        $tn_height = $height; }
    else {
        $tn_width  = 200;
        $tn_height = int( ($height * (200) ) / $width );
        if ($tn_height > 200) {
				    $tn_width  = int( ( $width * (200) ) / $height );
				    $tn_height = 200; }}
    my ($safe_width) = $tn_width =~ /^([0-9]+)$/;
    if (!$safe_width) { abort('Tainted width'); }
    my ($safe_height) = $tn_height =~ /^([0-9]+)$/;
    if (!$safe_height) { abort('Tainted height'); }
	my $dir = DIR;
    my ($safe_source_file) = $source_file =~ /^($dir\/src\/[0-9]+\.[\w]+(\[0\])?)$/;
    if (!$safe_source_file) { abort('Tainted source file'); }
    my ($safe_thumbnail) = $thumbnail =~ /^($dir\/thumb\/[0-9]+\.[\w]+)$/;
    if (!$safe_thumbnail) { abort('Tainted thumbnail'); }
    local $ENV{"PATH"} = "/usr/local/bin:/usr/bin:/bin";
    local $ENV{"BASH_ENV"} = "";
    # ImageMagick
    `convert -size ${safe_width}x${safe_height} -geometry ${safe_width}x${safe_height}! -quality THUMBNAIL_QUALITY $safe_source_file $safe_thumbnail`;
    return 1 unless ($?);
	  # PerlMagick
	  eval 'use Image::Magick';
	  unless($@) {
		    my ($res,$magick);
		    $magick = Image::Magick->new;
		    $res = $magick->Read($safe_source_file);
		    return 0 if "$res";
		    $res = $magick->Scale(width => $safe_width, height => $safe_height);
		    $res = $magick->Write(filename => $safe_thumbnail, quality => THUMBNAIL_QUALITY);
		    return 1; }
    # GD library
    eval 'use GD';
    $safe_source_file =~ s/\[0\]$//;
    my $srcImage;
    if ($safe_source_file =~ /\.jpg$/) {
        $srcImage = new GD::Image->newFromJpeg($safe_source_file); }
    elsif ($safe_source_file =~ /\.png$/) {
        $srcImage = new GD::Image->newFromPng($safe_source_file); }
    elsif ($safe_source_file =~ /\.gif$/) {
        $srcImage = new GD::Image->newFromGif($safe_source_file); }
    my $thumb = new GD::Image($safe_width, $safe_height);
    $thumb->copyResized($srcImage, 0, 0, 0, 0, $safe_width, $safe_height, $width, $height);
    open OUT, '>', $safe_thumbnail;
    binmode OUT;
    print OUT $thumb->jpeg();
    close OUT;
    return 1; }

sub verify_image($$$$$$$$) {
    my ($hash, $time, $ip, $filename, $extension, $size, $width, $height) = @_;
    my $abort;
    for (SUPPORTED_FILETYPES) {
        our $found = 1 if $extension eq $_; }
    $abort = 'File is empty' if !$size;
    $abort = 'File type is not supported' if !$main::found;
    $abort = 'Image exceeds maximum image width' if $width > 16384;
    $abort = 'Image exceeds maximum image height' if $height > 16384;
    $abort = 'Image exceeds maximum resolution' if ($width * $height) > 50000000;
    $abort = 'File size is too big' if $size > convert_kb_bytes(MAXIMUM_FILESIZE);
    $abort = 'Disallowed characters in filename' if $filename =~ /[ \.\/]/g;
    open my $database, '<', DIR . '/uploads.txt';
    flock $database, LOCK_SH;
    while (<$database>) {
        /([^\s]+) ([^\s]+) ([^\s]+) ([^\s]+) ([^\s]+) /;
        my ($db_id, $db_hash, $db_time, $db_ip, $db_filename) = ($1, $2, $3, $4, $5);
        our $count_first++;
        if ($main::count_first eq 1) {
            my $delay = $time - $db_time;
            if ($delay < 10) {
                $abort = 'Flood detected';
                last; }}
        if ($hash eq $db_hash) {
             $abort = 'Duplicate file found';
             last; }
        if ($filename =~ /^$db_filename$/i) {
             $abort = 'Duplicate file name found';
             last; }}
    close $database;
    return $abort; }

sub add_entry($$$$$$$$) {
    my ($hash, $time, $ip, $filename, $extension, $size, $width, $height) = @_;
    my $id;
    open my $database, '<', DIR . '/uploads.txt';
    flock $database, LOCK_SH;
    while (<$database>) {
        /^([0-9]+) /;
        $id = $1 + 1;
        last; }
    close $database;
    $id = 1 unless $id;
    open my $temporary, '>', DIR . '/uploads.tmp';
    flock $temporary, LOCK_EX;
    open my $database, '<', DIR . '/uploads.txt';
    flock $database, LOCK_SH;
    print $temporary "$id $hash $time $ip $filename $extension $size $width $height\n";
    while (<$database>) {
        chomp;
        print $temporary "$_\n"; }
    close $temporary;
    close $database;
    rename DIR . '/uploads.tmp', DIR . '/uploads.txt' or abort('Could not edit the database file');
    return $id; }

sub get_dirsize {
    my $size = 0;
    for (glob(DIR . "/src/*")) {
        $size += -s $_; }
    for (glob(DIR . "/thumb/*")) {
        $size += -s $_; }
    return $size; }

sub convert_kb_bytes {
    my $kb = shift;
    return 1024 * $kb; }

sub convert_bytes_readable {
    my $b = shift;
    if ($b > 1024 ** 3) {
        $b = $b / 1024 ** 3;
        $b =~ s/(\.[\d]{2})[\d]+$/$1/;
        $b .= ' GB'; }
    elsif ($b > 1024 ** 2) {
        $b = $b / 1024 ** 2;
        $b =~ s/(\.[\d]{2})[\d]+$/$1/;
        $b .= ' MB'; }
    elsif ($b > 1024) {
        $b = $b / 1024;
        $b =~ s/(\.[\d]{2})[\d]+$/$1/;
        $b .= ' kB' }
    else {
        $b .= ' B' }
    return $b; }

sub redirect {
    print
        "Content-type: text/html\n\n"
      . '<!DOCTYPE html>'
      . '<html><head>'
      . '<title></title>'
      . '<meta http-equiv="refresh" content="3;'
      . ' url=' . DIR . '">'
      . '</head><body>'
	  ;
	  if (-e "updating.html"){
	  print include("updating.html");}
	  else{
	  print 'Updating...';}
	  print '</body></html>'
      ; }

sub analyze_image {
    my $upload = shift;
    my $filename = $upload;
    my ($file, $ext) = $filename =~ /^(.*)\.([^\.]+)$/;
    my $size =-s $upload;
    my (@res);
    return ($file, $size, "jpg", @res) if (@res = analyze_jpeg($upload));
    return ($file, $size, "png", @res) if (@res = analyze_png($upload));
    return ($file, $size, "gif", @res) if (@res = analyze_gif($upload));
    return ($file, $size, lc($ext), 0, 0); }

sub analyze_jpeg {
    my $file = shift;
    my ($buffer);
    read($file, $buffer, 2);
    if ($buffer eq "\xff\xd8") {
      OUTER:
        for (; ;) {
            for (; ;) {
                last OUTER unless (read($file, $buffer, 1));
                last if ($buffer eq "\xff"); }
            last unless (read($file, $buffer, 3) == 3);
            my ($mark, $size) = unpack("Cn", $buffer);
            last if ($mark == 0xda or $mark == 0xd9);
            abort("Possible virus in image") if ($size < 2);
            if ($mark >= 0xc0 and $mark <= 0xc2) {
                last unless (read($file, $buffer, 5) == 5);
                my ($bits, $height, $width) = unpack("Cnn", $buffer);
                seek($file, 0, 0);
                return ($width, $height); }
            seek($file, $size - 2, 1); }}
    seek($file, 0, 0);
    return (); }

sub analyze_png {
    my $file = shift;
    my ($bytes, $buffer);
    $bytes = read($file, $buffer, 24);
    seek($file, 0, 0);
    return () unless ($bytes == 24);
    my ($magic1, $magic2, $length, $ihdr, $width, $height)
      = unpack("NNNNNN", $buffer);
    return () unless (
          $magic1 == 0x89504e47
      and $magic2 == 0x0d0a1a0a
      and $ihdr == 0x49484452 );
    return ($width, $height); }

sub analyze_gif {
    my $file = shift;
    my ($bytes, $buffer);
    $bytes = read($file, $buffer, 10);
    seek($file, 0, 0);
    return () unless ($bytes == 10);
    my ($magic, $width, $height) = unpack("A6 vv", $buffer);
    return () unless ($magic eq "GIF87a" or $magic eq "GIF89a");
    return ($width, $height); }

sub RC4 {
    my $MAX_CHUNK_SIZE = 1024;
    my $self;
    my (@state, $x, $y);
    if (ref $_[0]) {
        $self  = shift;
        @state = @{ $self->{state} };
        $x     = $self->{x};
        $y     = $self->{y}; }
    else {
        @state = Setup(shift);
        $x = $y = 0; }
    my $message    = shift;
    my $num_pieces = do {
        my $num = length($message) / $MAX_CHUNK_SIZE;
        my $int = int $num;
        $int == $num ? $int : $int + 1; };
    for my $piece (0 .. $num_pieces - 1) {
        my @message = unpack "C*", substr($message, $piece * $MAX_CHUNK_SIZE, $MAX_CHUNK_SIZE);
        for (@message) {
            $x = 0 if ++$x > 255;
            $y -= 256 if ($y += $state[$x]) > 255;
            @state[ $x, $y ] = @state[ $y, $x ];
            $_ ^= $state[ ($state[$x] + $state[$y]) % 256 ]; }
        substr($message, $piece * $MAX_CHUNK_SIZE, $MAX_CHUNK_SIZE) = pack "C*", @message; }
    if ($self) {
        $self->{state} = \@state;
        $self->{x}     = $x;
        $self->{y}     = $y; }
    $message; }

sub Setup {
    my @k     = unpack('C*', shift);
    my @state = 0 .. 255;
    my $y     = 0;
    for my $x (0 .. 255) {
        $y = ($k[ $x % @k ] + $state[$x] + $y) % 256;
        @state[ $x, $y ] = @state[ $y, $x ]; }
    wantarray ? @state : \@state; }

sub encode_base64 {
    my $data = shift;
    my $res = pack "u", $data;
    $res =~ s/^.//mg;
    $res =~ s/\n//g;
    $res =~ tr| -_|AA-Za-z0-9+/|;
    my $padding = (3 - length($data) % 3) % 3;
    $res =~ s/.{$padding}$/'='x$padding/e if ($padding);
    $res =~ s/(.{1,76})/$1/g;
    return $res; }

sub decode_base64 {
    my $str = shift;
    $str =~ tr|A-Za-z0-9+=/||cd;
    $str =~ s/=+$//;
    $str =~ tr|A-Za-z0-9+/| -_|;
    return "" unless (length $str);
    return unpack "u", join '', map { chr(32 + length($_) * 3 / 4) . $_ } $str =~ /(.{1,60})/gs; }

sub build_pages {
    my $index = shift;
    open my $database, '<', DIR . '/uploads.txt';
    flock $database, LOCK_SH;
    while (<$database>) {
        our $count_uploads++; }
    close $database;
    my $pages = $main::count_uploads / 20;
    $pages = int($pages + 1) if $pages != int $pages or $pages == 0;
    for (my $a = 1; $a <= $pages; $a++) {
        my $page_name = $a;
        $page_name = 'index' if $page_name == 1;
        my ($first, $last) = process_page($a, $main::count_uploads);
        for (SUPPORTED_FILETYPES) {
            our $filetypes .= "$_ "; }
        open PAGE, '>' ,DIR . '/' . $page_name . '.html';
        flock PAGE, LOCK_EX;
	my $css = -e "style.css" ? "../style.css" : "../../style.css";
        print PAGE
            '<!DOCTYPE html>'
          . '<html lang="en">'
          . '<head>'
          . '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
		  . '<meta id="meta" name="viewport" content="width=device-width; initial-scale=1.0">'
          . '<title>Images</title>'
		  . '<link rel="stylesheet" href="' . $css . '">'
          . '<script type="text/JavaScript">'
          . 'function insert(text){'
          . 'document.del.file.value=text;'
          . 'document.del.file.focus();}'
          . '</script>'
          . '</head>'
          . '<body id="image">'
		  . '<div class="shell"><div class="boardnav">'
		  ;
		my $n = 0;
		my $nav = '<span>[ ';
        for (my $b = 1; $b <= $pages; $b++) {
			$nav .= ' / ' if ($n != 0);
			$n++;
            if ($a eq $b) {
                $nav .= $b; }
            else {
                my $b_page = $b . '.html';
                $b_page = 'index.html' if $b_page == 1;
                $nav .= '<a href="' . $index . $b_page . '">' . $b . '</a>'; }}
		$nav .= ' ]</span>';
		if ($a - 1 >= 1) {
            my $previous = ($a - 1) . '.html';
            $previous = 'index.html' if $previous == 1;
            $nav .= '<span>[ <a href="' . $index . $previous . '">Previous</a> ]</span>'; }
		if ($a + 1 <= $pages) {
            my $next = $a + 1;
            $nav .= '<span>[ <a href="' . $index . $next . '.html">Next</a> ]</span>'; }
		$nav .= '<span class=right>[ <a href="../index.html">Return</a> ]</span>';
		print PAGE  $nav . '</div></div><div class="grid">';
        my $inc;
        open my $database, '<', DIR . '/uploads.txt';
        flock $database, LOCK_SH;
        while (<$database>) {
            /^([^\s]+) ([^\s]+) ([^\s]+) ([^\s]+) ([^\s]+) ([^\s]+) ([^\s]+) ([^\s]+) ([^\s]+)$/;
            my ($id, $hash, $time, $ip, $filename, $extension, $size, $width, $height) = ($1, $2, $3, $4, $5, $6, $7, $8, $9);
            $inc++;
            if ($inc >= $first) {
                if ($extension =~ /^(jpg|gif|png)$/) {
                    print PAGE
                        '<div class="shell-thread thumb"><div>'
                      . '<span class="image">'
                      . '<a href="' . $id . '/' . $filename . '.' . $extension . '" target="_blank">'
                      . '<img src="' . 'thumb/' . $id . '.jpg" alt="' . $filename . '" title="' . $filename . '.' . $extension . ' (' . $width . ' &#215;  ' . $height . ', ' . convert_bytes_readable($size) . ')">'
                      . '</a>'
                      . '</span>'
                      . '<span class="info">'
                      . '<span><small>' . $filename . '.' . $extension 
					  . '<span class="hide">(' . $width . ' &#215;  ' . $height . ', ' . convert_bytes_readable($size) . ')</span>'
					  . '</small></span><br>'
                      . '<span class="id" onClick="insert(' . $id . ')">No. ' . $id . '</span>'
                      . '</span>'
                      . '</div></div>'
                      ; }
                else {
                    print PAGE 'No thumbnail'; }}
            last if $inc == $last; }
        close $database;
        print PAGE
		    '</div>'
          . '<div id="imgbar" class="shell">'
		  . '<div class="boardnav">' . $nav . '</div>'
		  . '<div class="admin">'
		  . '<form action="' . $index . 'upload.cgi" method="get" name="del">'
          . '<table>'
          . '<tr><td>No.</td><td><input type="text" size="4" name="file"> <input type="submit" value="Delete"></td></tr>'
          . '<tr><td>Admin:</td><td><input type="text" size="4" name="admin"></td></tr>'
          . '</table></form>'
		  . '</div><div>'
		  . '<div id="upload">'
          . '<form action="../upload.cgi" method="post" enctype="multipart/form-data">'
          . '<input type="file" name="upload">'
		  . '<input type="submit" value="Upload">'
          . '<input type="reset" value="Cancel"></br>'
		  . '<small>Maximum file size allowed: ' . convert_bytes_readable(convert_kb_bytes(MAXIMUM_FILESIZE)) . ' '
		  . '&#8251; Supported file types: jpg png gif<br>'
          . '<p>Used: ' . convert_bytes_readable(get_dirsize())
		  ;
		  if (PRUNING_SIZE){print PAGE ' / ' . convert_bytes_readable(PRUNING_SIZE*1024)};
		  print PAGE
            '</p></small></form></div>'
		  . '</div></div>'
          . '</body>'
          . '</html>'
          ;
        close PAGE; }}

sub process_page($$) {
    my ($page, $count) = @_;
    my $last = $page * 20;
    my $first = $last - 19;
    if ($last > $count) {
        $last = $count; }
    return ($first, $last); }

sub print_delete_page($$$) {
    my ($index, $id, $admin) = @_;
    print "Content-type: text/html\n\n";
    print
        '<!DOCTYPE html>'
      . '<html lang="en">'
      . '<head>'
      . '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
      . '<title>Delete upload</title>'
      . '<link rel="stylesheet" type="text/css" href="style.css">'
      . '</head>'
      . '<body>'
      . '<form action="' . $index . 'upload.cgi" method="get">'
      . '<input type="hidden" name="file" value="' . $id . '">'
      . '<input type="hidden" name="admin" value="' . $admin . '">'
      . '<input type="hidden" name="confirm" value="1">'
      . '<b>Do you want to delete upload No.' . $id . '?</b> '
      . '<input type="submit" value="Delete">'
      . '</form>'
      . '</body>'
      . '</html>'
      ; }

sub delete_upload {
    my $id = shift;
    open my $temporary, '>', DIR . '/uploads.tmp';
    flock $temporary, LOCK_EX;
    open my $database, '<', DIR . '/uploads.txt';
    flock $database, LOCK_SH;
    while (<$database>) {
        chomp;
        /^([^\s]+) ([^\s]+) ([^\s]+) ([^\s]+) ([^\s]+) ([^\s]+) /;
        my ($db_id, $db_filename, $db_extension) = ($1, $5, $6);
        if ($id eq $db_id) {
            my $source_file = DIR . '/src/' . $db_id . '.' . $db_extension;
            my $thumbnail = DIR . '/thumb/' . $db_id . '.' . 'jpg';
            unlink($source_file);
            unlink($thumbnail); }
        else {
            print $temporary "$_\n"; }}
    close $temporary;
    close $database;
    rename DIR . '/uploads.tmp', DIR . '/uploads.txt' or abort('Could not edit the database file'); }

sub abort {
    my $msg = shift;
    print "Content-type: text/html\n\n";
    print '<h1>Software error:</h1><pre>' . $msg . '</pre>';
    exit; }
	
sub include($) {
    my ($file) = @_;
    open my $read, '<', "$file";
    my $content = do { local $/; <$read> };
    close $read;
    $content =~ s/[\r\n]//g;
    return $content;
}

sub pruning {
	if (PRUNING_NUMBER || PRUNING_SIZE){
		my $f = DIR . "/uploads.txt"; 
		my $n = "0"; 
		open (TXT,"$f");seek (TXT,0,0); 
		while (my $line = <TXT>) { 
			$n++; 
			my @delinfo = split / /, $line;
			if ($n >= PRUNING_NUMBER && PRUNING_NUMBER){
				delete_upload(@delinfo[0]); 
			}elsif (get_dirsize() > convert_kb_bytes(PRUNING_SIZE) && PRUNING_SIZE){
				delete_upload(@delinfo[0]);
			}
		};
		close (TXT);
	}
}