var toggle_class = function(targetClass, newClass, action) {
	var x = document.getElementsByClassName(targetClass);
	var i; for (i = 0; i < x.length; i++) {
		if (action != null){
			x[i].classList.toggle(newClass, action);
		}else{
			x[i].classList.toggle(newClass);
		}
	}
};

var set_cookie = function(cookieValue, cookieName) {
    var today = new Date();
    var expire = new Date();
    expire.setTime(today.getTime() + 3600000*24*90);
    document.cookie = cookieName+"="+escape(cookieValue) + ";expires="+expire.toGMTString() + ";path=/";
};

var set_inputs = function() {
    var i=0;
    for (i=0;i<=document.forms.length-1;i++) {
        with(document.forms[i]) {
            if(!name.value) {name.value=get_cookie("name");}
        }
    }
};

var toggle_mona = function() {
	var x = document.getElementById("monatoggle");
	if (x.classList.contains('active') != 0){
		set_cookie('no','mona');
	}else{
		load_mona();
		set_cookie('yes','mona');
	};
	x.classList.toggle('active');
};

var load_mona = function() {
	var css = document.createElement("style");
	css.type = "text/css";
	css.innerHTML = '@font-face {  font-family: "Mona"; src: url(/mona.woff) format("woff"); ';
	document.body.appendChild(css);
}

var get_cookie = function(name) {
    with(document.cookie) {
        var regexp=new RegExp("(^|;\\s+)"+name+"=(.*?)(;|$)");
        var hit=regexp.exec(document.cookie);
        if (hit&&hit.length>2) return unescape(hit[2]);
        else return '';
    }
};

var set_button = function( optionValue, optionMenu){
	toggle_class(optionMenu , "active", 0);
	toggle_class(optionMenu + ' ' + optionValue, "active", 1);
};

var iso_layout = function(layoutValue){
		var y = (layoutValue != "vertical");
		toggle_class("shell-thread", "columnwidth", y);
		set_cookie(layoutValue, "layout");
		set_button(layoutValue, "layout");
		iso.arrange({layoutMode: layoutValue});

};

var iso_sort = function(sortValue){
		set_cookie(sortValue, "sort");
		set_button(sortValue, "sort");
		iso.arrange({sortBy: sortValue});
};

var iso_filter = function(filterValue){
		set_cookie(filterValue, "filter");
		set_button(filterValue, "filter");
		var r = document.getElementsByClassName('shell-thread');
		var i; for (i = 0; i < r.length; i++) {
			var itemElem = r[i];
			iso.arrange({
				filter: function( itemElem ) {
					var timestamp = itemElem.getElementsByClassName('lastpost')[0].textContent;
					if (filterValue != 0 ){
							return (((new Date).getTime() / 1000 | 0) - timestamp  < filterValue);
						}else{ return 1;};
				}
			});
		};
};

var quote = function(postnumber,thread) {
    toggle_class(thread , "hide", 0);
	iso.arrange();
    var text = '>>'+postnumber+'\n';
    var textarea=document.getElementById("form"+thread).message;
    if(textarea) {
        if(textarea.createTextRange && textarea.caretPos) {
            var caretPos=textarea.caretPos;
            caretPos.text=caretPos.text.charAt(caretPos.text.length-1)==" "?text+" ":text;
        }
        else if(textarea.setSelectionRange) {
            var start=textarea.selectionStart;
            var end=textarea.selectionEnd;
            textarea.value=textarea.value.substr(0,start)+text+textarea.value.substr(end);
            textarea.setSelectionRange(start+text.length,start+text.length);
        }
        else {
            textarea.value+=text+" ";
        }
        textarea.focus();
    }
    textarea.setSelectionRange(4097,4097);
};


var quick_reply = function(thread) {
    toggle_class(thread , "hide");
	iso.arrange();
};

window.onload = function() { 
	set_inputs();
	var mcookie = get_cookie('mona');
	if (mcookie == 'yes'){load_mona();};

	var frontpage = document.getElementById('frontpage');
	if (frontpage != null){
		//toggle_class("shell-thread", "columnwidth");
		toggle_class("form", "hide");
		toggle_class("form shell", "hide");
		toggle_class("quickreplytoggle", "hide");
		toggle_class("threadlistlink", "hide");
		toggle_class("optiontoggle", "hide");
	
		iso = new Isotope( '.grid', {
			itemSelector: '.shell-thread',
			layoutMode: 'vertical',
			percentPosition: true,
			transitionDuration: '0s',
			getSortData: {
				lastbump: '.lastbump parseInt',
				lastpost: '.lastpost parseInt',
				threadage: '.threadage parseInt',
				postcount: '.postcount parseInt'
			},
			sortAscending: {
				lastbump: false,
				lastpost: false,
				threadage: true,
				postcount: false
			},
			masonry: {
				columns: 2
			},
		});
		window.onorientationchange = function(){
		   iso.arrange();
		}

		var lcookie = get_cookie('layout');
		if (lcookie != ''){ iso_layout(lcookie);
		}else{set_button('vertical', 'layout');}
		
		var scookie = get_cookie('sort');
		if (scookie != ''){ iso_sort(scookie);
		}else{set_button('lastbump', 'sort');}
		
		var fcookie = get_cookie('filter');
		if (fcookie != ''){ iso_filter(fcookie);
		}else{set_button( 0, 'filter');}
	
	}else if(document.getElementById('threadpage') != null){
		
		document.onmousemove = function(e){
			cursorX = e.pageX;
			cursorY = e.pageY;
		}	
		box = document.getElementById("hover");
		var x = document.getElementsByClassName('postlink');
		var i; for (i = 0; i < x.length; i++) {
			x[i].onmouseover = function () {var href = this.href.split('/');set_hover(href[href.length - 1])}
			x[i].onmouseout = function () {reset_hover();}
		};
	};
}

var set_hover = function(target){
	var array = target.split(',');
	for (var i = 0; i < array.length; i++) {
		if (array[i].indexOf('-') === -1){
			var x=document.getElementById(array[i])
			if (x !== null){box.innerHTML += '<div class="post">' + x.innerHTML + '</div>'}
		}else{
			box.innerHTML += '<div class="post"><span class="num">' + array[i] + '</span>' +
			'<div class="comment"><i>Click link to see entire range of posts.</i></div></div>';
		};
	};
	
	if (window.innerWidth - cursorX > box.offsetWidth){
		box.style.left = cursorX + 'px';
	}else{
		box.style.left = 'initial';
		box.style.right = 10 + 'px';
	}
	if(box.offsetHeight > window.innerHeight || (cursorY - window.pageYOffset) < box.offsetHeight/2){
		box.style.top = 10 + 'px';
	}else if (box.offsetHeight/2 < window.innerHeight - (cursorY - window.pageYOffset)){
		box.style.top = (cursorY - window.pageYOffset) - box.offsetHeight/2 + 'px';
	}else{
		box.style.bottom = 10 + 'px';
	};
}
var reset_hover = function(){
	box.innerHTML = ""
	box.style.left=-2000+'px'
	box.style.top='initial'
	box.style.bottom='initial'
}
