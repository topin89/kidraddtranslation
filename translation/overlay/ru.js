/*
 * Kid Radd — Russian edition additions (loaded after radd.js).
 *
 * 1. Translator Notes: a "notes" button in the empty middle cell of every
 *    panel's bottom bar. Greyed out when the panel has no note.
 *    Data: window.KR_NOTES = {panelName: "<p>html</p>", ...} (inlined per page).
 * 2. Animation-end cue: when the visible panel shows a play-once GIF that runs
 *    for at least ANIM_THRESHOLD_MS, the "next" arrow starts pulsing once the
 *    animation reaches its last frame.
 *    Data: window.KR_ANIM = {"file.gif": msUntilLastFrame, ...} (kr-anim.js).
 */
(function($) {
	var ANIM_THRESHOLD_MS = 3000;
	var UI = $.extend({notes: 'notes', heading: 'Translator notes', close: 'close'}, window.KR_UI || {});
	var NOTES = window.KR_NOTES || {};
	var ANIM = window.KR_ANIM || {};
	var timer = null;

	function basename(url) {
		return (url || '').split(/[?#]/)[0].split('/').pop();
	}

	// ---------------------------------------------------------------- notes

	function buildPopup() {
		var overlay = $('<div id="kr-note-overlay"><div id="kr-note" role="dialog" aria-modal="true">' +
			'<h3></h3><div class="kr-note-body"></div>' +
			'<button type="button" class="kr-note-close"></button></div></div>');
		overlay.find('h3').text(UI.heading);
		overlay.find('.kr-note-close').text(UI.close).on('click', closeNote);
		overlay.on('click', function(e) { if (e.target === this) closeNote(); });
		$(document.documentElement).append(overlay);
	}

	function openNote(panel) {
		if (!NOTES[panel]) return;
		$('#kr-note .kr-note-body').html(NOTES[panel]);
		$('#kr-note-overlay').addClass('open');
	}

	function closeNote() {
		$('#kr-note-overlay').removeClass('open');
	}

	function addButtons() {
		$('a.panel').each(function() {
			var panel = $(this).attr('name');
			var zoom = $(this).find('a[href="javascript:zoom()"]');
			if (!zoom.length) return;
			// Bottom bar: <td height=30>zoom</td><td height=30></td><td height=30>list</td>
			var cell = zoom.parents('td[height="30"]').first().next('td');
			if (!cell.length) return;
			var has = !!NOTES[panel];
			var btn = $('<table border="0" cellpadding="0" cellspacing="0" width="39" height="19"><tr>' +
				'<td background="menu.gif"><center><font face="verdana" size="1">' +
				'<span class="kr-notes-btn"></span></font></center></td></tr></table>');
			btn.find('.kr-notes-btn').text(UI.notes);
			if (has) {
				btn.attr('title', UI.heading).on('click', function(e) {
					e.preventDefault();
					openNote(panel);
				});
			} else {
				btn.addClass('kr-notes-off');
			}
			if ($.trim(cell.text()) === '') {
				cell.append($('<center></center>').append(btn));
			} else {
				// Last panel: the middle cell holds the copyright line; put the button beside it.
				var row = $('<table border="0" cellpadding="0" cellspacing="0" align="center"><tr>' +
					'<td></td><td width="8"></td><td></td></tr></table>');
				row.find('td').first().append(cell.contents());
				row.find('td').last().append(btn);
				cell.append(row);
			}
		});
	}

	// ----------------------------------------------------- animation cue

	function onPanelShown() {
		clearTimeout(timer);
		$('img.kr-pulse').removeClass('kr-pulse');
		closeNote();
		var panel = $('a.panel.visible').first();
		if (!panel.length) return;
		var longest = 0;
		panel.find('img').each(function() {
			var ms = ANIM[basename($(this).attr('src'))];
			if (!ms) return;
			// radd.js restarts the swapped-in "imageflip" GIFs on every panel change;
			// restart other play-once GIFs too, so the cue matches what is on screen.
			var name = $(this).attr('name') || '';
			if (name.indexOf('imageflip') < 0) {
				var src = $(this).attr('src');
				$(this).attr('src', 'spacer.gif').attr('src', src);
			}
			if (ms > longest) longest = ms;
		});
		if (longest >= ANIM_THRESHOLD_MS) {
			timer = setTimeout(function() {
				panel.find('img[src="next.gif"]').addClass('kr-pulse');
			}, longest);
		}
	}

	$(document).ready(function() {
		buildPopup();
		addButtons();
		$(window).bind('hashchange', onPanelShown);
		$(document).keydown(function(e) {
			if (e.keyCode == 27) closeNote();
		});
		onPanelShown();
	});
})(jQuery);
