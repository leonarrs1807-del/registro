"""Shared sky-blue table palette for the desktop and Excel files."""
HEADER='#E0F2FE'
HEADER_TEXT='#075985'
BORDER='#BAE6FD'
SELECTED='#BAE6FD'


def button():
    return dict(fg_color=('#BAE6FD','#075985'),hover_color=('#7DD3FC','#0369A1'),
                text_color=('#075985','#F0F9FF'),border_width=1,border_color=('#7DD3FC','#0369A1'))


def tabs():
    return dict(fg_color=('#F0F9FF','#0C4A6E'),selected_color=('#7DD3FC','#0369A1'),
                selected_hover_color=('#38BDF8','#0284C7'),unselected_color=('#E0F2FE','#0C4A6E'),
                unselected_hover_color=('#BAE6FD','#075985'),text_color=('#075985','#F0F9FF'))
