use strict;

sub markup($$$$) {
    my ($str, $dir, $board, $thread) = @_;
	my $siteurl = SITE_URL;
    $str =~ s/&gt;&gt;(([1-9][0-9]*[\-\,]?)+)/<a href="$dir\/read.cgi\/$board\/$thread\/$1" class="postlink">&gt;&gt;$1<\/a>/g;
	$str =~ s/((https?):\/\/$siteurl([^\s]+))/<a href="$3">&rarr;$3<\/a>/g;
    my $urlpattern = qr{(?:https?|ftp)://[a-z0-9-]+(?:\.[a-z0-9-]+)+(?::[0-9]{4})?(?:[/?](?:[\x21-\x25\x27-\x5A\x5E-\x7E]|&amp;)+)?};
    $str =~ s/($urlpattern)/my $l = markup_escape($1); '<a href="' . $l . '">' . $l . '<\/a>'/eg;
    $str =~ s/^@@(\n[^\n])/\x{3000}$1/gm;
    $str =~ s/(^|\n+)(\x{3000}.+?)(\n\n+|\Z)/$1 . '<p><span lang="ja">' . markup_escape($2) . '<\/span><\/p>' . $3/emgs;
    $str =~ s/(<span lang="ja">)\x{3000}\n/$1/g;

    my @tags = (
                '#'       # bracket escape
              , 'code'    # code (also escapes brackets)
              , 'b'       # bold
              , 'i'       # italics
              , 'o'       # overline
              , 'u'       # underline
              , 's'       # strikethrough
              , 'aa'      # sjis font
              , 'm'       # monospace font
              , 'spoiler' # spoiler
              , 'sup'     # subscript
              , 'sub'     # superscript
               );

    my $malformed; # flag for malformed BBCode


    for (@tags) { # parse tags one by one
        my $tag = $_;
        if ($tag =~ /^(#|code)$/) { # TAGS THAT DO NOT NEED NESTING

            while ($str =~ /(.*?)\[$tag\](.*?)\[\/$tag\](.*)$/gs) {

                my ($left, $content, $right) = ($1, $2, $3);

                $content =~ s/\[/&#91;/g;
                $content =~ s/\]/&#93;/g;
                $content =~ s/&gt;/&#gt;/g;

                if ($tag =~ /^(#)$/) {
                    $str = $left . $content . $right;
                }
                elsif ($tag =~ /^(code)$/) {
                    $str = $left . '<code>' . $content . '</code>' . $right;
                }
            }

        }
    }

    # QUOTE NESTING
    while ($str =~ /(.*\n(&gt;\s?)*|\A(&gt;\s?)*)&gt;\s?(.*?)(\n.*|\Z)/gs) {
        my ($left, $content, $right) = ($1, $4, $5);

        $str = $left . '<blockquote>' . $content . '</blockquote>' . $right;
    }
    $str =~ s/&#gt;/&gt;/g; # bring back "escaped" >
    while ($str =~ /(.*)(<\/blockquote>)\n(<blockquote>)(.*)/gs) {
        my ($left, $right) = ($1, $4);
        $str = $left . "\n" . $right;
    }
    $str =~ s/<\/blockquote>\n/<\/blockquote>/g;
    for (@tags) { # escape unclosed tags from a blockquote
        my $tag = $_;
        while ($str =~ /(.*)\[($tag)\](.*?)(<\/?(?:blockquote).*?>)(.*)/mgs) {
            if ($3 !~ /\[\/$2\]/g) {
                $str = "$1&#91;$2&#93;$3$4$5";
                $malformed++;
            }
        }
    }

    for (@tags) {
        my $tag = $_;
        if ($tag !~ /^(#|code)$/) { # TAGS THAT CAN BE NESTED

            while ($str =~ /(.*)\[$tag\](.*?)\[\/$tag\](.*)/gs) {

                my ($left, $content, $right) = ($1, $2, $3);

                my $fail;

                for (@tags) {
                    my $tagcheck = $_;
                    my $balance;
                    $balance++ while $content =~ /\[$tagcheck\]/g;
                    $balance-- while $content =~ /\[\/$tagcheck\]/g;

                    $fail = 1 if $balance > 0 or $balance < 0;
                }

                unless ($fail) {

                    if ($tag =~ /^(b|i|sup|sub)$/) {
                        $str = $left . '<' . $tag . '>' . $content . '</' . $tag . '>' . $right;
                    }
                    elsif ($tag =~ /^(o)$/) {
                        $str = $left . '<span style="text-decoration:overline">' . $content . '</span>' . $right;
                    }
                    elsif ($tag =~ /^(u)$/) {
                        $str = $left . '<u>' . $content . '</u>' . $right;
                    }
                    elsif ($tag =~ /^(s)$/) {
                        $str = $left . '<s>' . $content . '</s>' . $right;
                    }
                    elsif ($tag =~ /^(m)$/) {
                        $str = $left . '<samp>' . $content . '</samp>' . $right;
                    }
                    elsif ($tag =~ /^(spoiler)$/) { # Other: self-classed span tags
                        $str = $left . '<span class="' . $tag . '">' . $content . '</span>' . $right;
                    }
                    elsif ($tag =~ /^(aa)$/) {
                        $str = $left . '<span lang="ja">' . $content . '</span>' . $right;
                    }
                }
                else {
                    $str = $left . '&#91;' . $tag . '&#93;' . $content . '&#91;/' . $tag . '&#93;' . $right;
                    $malformed++;
                }
            }
        }
    }

    for (@tags) { # any stray tags are considered malformed markup
        my $tag = $_;
        $malformed++ while $str =~ /\[$tag\]/g;
        $malformed++ while $str =~ /\[\/$tag\]/g;
    }
    $str =~ s/\n/<br>/g;
    return markup_unescape($str, 0);
}

sub markup_escape($) {
    my $str = shift;
    $str =~ s/&gt;/\x{1F}A/g;
    $str =~ s/^``/\x{1F}B/g;
    $str =~ s/'/\x{1F}C/g;
    return $str;
}

sub markup_unescape($) {
    my $str = shift;
    $str =~ s/\x{1F}A/&gt;/g;
    $str =~ s/\x{1F}B/``/g;
    $str =~ s/\x{1F}C/'/g;
    return $str;
}
1;
