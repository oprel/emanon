#!/usr/bin/perl -Tw

use strict;
use CGI::Carp 'fatalsToBrowser';
use Fcntl ':flock';
use File::ReadBackwards;
use lib '.';

use constant RECENT_NUMBER =>	15;					#How many posts to load.
use constant SHOW_ALL	   =>	0;					#Also display saged posts? (0 = no, 1 = yes)
use constant FILTER_BOARDS => ('time','sageru');	#Pick which boards not to display.

my $dir     = $ENV{'SCRIPT_NAME'};
  ($dir)    = $dir =~ /^(.*)\/[^\/]*$/;

open my $read, '<', "all.html" || die "Cannot read static file: $!";
flock $read, LOCK_SH;
my $static = <$read>;
my ($logtime) = $static =~ /<!--([0-9]+)-->/;
close $read;
if ((stat("log.txt"))[9] eq $logtime){
	print "Content-type: text/html\n\n $static";
}else{
    open my $write, '>:utf8', "all.html" || die "Cannot write file: $!";
    flock $write, LOCK_EX;
    print $write
      '<!DOCTYPE html>'
    , '<html lang="en">'
	, '<!--' . (stat("log.txt"))[9] . '-->'
	, '<head><meta charset="UTF-8"><meta id="meta" name="viewport" content="width=device-width; initial-scale=1.0">'
    , '<script src="' . $dir . '/isotope.pkgd.min.js"></script>'
    , '<script src="/script.js"></script>'
	, '<link rel="stylesheet" href="style.css">'
    , '<title>Recent Posts</title></head>'
	, '<body id="frontpage">'
    ;
	my ($i, %seen);
	my %fboards = FILTER_BOARDS;
	my $read = File::ReadBackwards->new("log.txt");
	while( defined( my $line = $read->readline ) ) {
		my ($log_ip, $lastpost, $board, $thread, $postnum, $sage) = $line =~ /^(.*?) ([0-9]+) (.*?) ([0-9]+) ([0-9]+) ([0-1])/;
		if (scalar(keys %seen ) eq 0){
			open my $read, '<:utf8', "$board/index.html" || die "Cannot read thread file: $!";
			flock $read, LOCK_SH;
			while (my $line = <$read>) {
				my ($navigation) = $line =~ /<div class=\"boardnav\">(.*?)<\/span><\/span><\/div>/;
				$navigation =~ s/<a href=\"(.*?)\">all<\/a>/all/;
				$navigation =~ s/ $board / <a href=\"$dir\/$board\">$board<\/a> /;
				$navigation =~ s/<span>\[ <a href=\"images\">Images<\/a> \]<\/span>//;
				$navigation =~ s/selected>/>/;
				$navigation =~ s/all.cgi\">/all.cgi\" selected>/;#"
				my ($options) = $line =~ /<div id=\"options\" class=\"optionmenu hide\">(.*?)&#8203;<\/div>/;
				print $write 
				  '<div class="shell"><div class="boardnav">' . $navigation . '</span></span></div>'
				, '<div id="options" class="optionmenu hide">' . $options
				, '</div><div style="text-align:center;padding:14px;">'
				, '<h2>Viewing ' . RECENT_NUMBER . ' recently active threads</h2>'
				, '</div></div>'
				, '<div class="grid">';
			};
		};
		if (!$seen{"$board/$thread"} and !exists($fboards{$board}) and (!$sage || SHOW_ALL)){
			$seen{"$board/$thread"} = 1;
			open my $read, '<:utf8', "$board/index.html" || die "Cannot read thread file: $!";
			flock $read, LOCK_SH;
			while (my $line = <$read>) {
				my ($content) = $line =~ /<div id=\"$thread\" class=\"shell-thread\"><div><div class=\"subject\"><span class=\"threadpost\">\[(?:[0-9]+):(?:[0-9]+)(.*?)<\/div><\/div><\/div>/;
				if ($content) {
					print $write
					 '<div id="' . "$board/$thread" . '" class="shell-thread"><div>'
					, '<div class="subject"><span class="threadpost">' . "[$board"
					, $content
					, '</a> </div></div></div>'
					;
				}else{
					print $write
					  '<div id="' . "$board/$thread"
					, '" class="shell-thread"><div><div class="subject"><span class="threadpost">'
					, "[$board]</span></div>"
					, '<div class="sortinfo hide"><span class="lastbump">' . $lastpost  . '</span><span class="lastpost">' . $lastpost  . '</span><span class="threadage">' . $thread . '</span><span class="postcount">' . $postnum . '</span></div>'
					, "<a href=\"$dir/read.cgi/$board/$thread\">"
					, '<div class="comment">A mysterious thread...</div></a></div></div>'
					;
				}
			}
			close $read; $i++;
			last if $i == RECENT_NUMBER;
		}else{ $seen{'x'} = 1 };
	}
    print $write '</div></body></html>';
	close $write;
	open my $read, '<', "all.html" || die "Cannot read static file: $!";
	flock $read, LOCK_SH;
	$static = <$read>;
	close $read;
	$static =~ s/ all / <i>all<\/i> /;
	print "Content-type: text/html\n\n"	. $static;
};