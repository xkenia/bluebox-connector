import requests
import time
import PySimpleGUI as sg

class Record(object):

    def __init__(self, card, code, time):
        
        self.card = card
        self.code = code
        self.time = time


def get_records_from_rawsplits(window, rawsplits_filename):

    try:
        file = open(rawsplits_filename,"r")
        rawsplits_str = file.read()
        file.close()

    except:
        window_terminal(window, 'Cannot read RawSplits file', 'WARN')
        return False

    records = []

    for line in rawsplits_str.split('\n'):
        if len(line) > 2:
            tmp = line.split('/')
            card = int(tmp[0].split(':')[0])
            code = int(tmp[0].split(':')[1])
            time = tmp[1]
            
            records.append(Record(card, code, time))

    return records

def get_finishes_from_rawsplits(window, rawsplits_filename, finish_code):

    try:
        file = open(rawsplits_filename,"r")
        rawsplits_str = file.read()
        file.close()

    except:
        window_terminal(window, 'Cannot read RawSplits file', 'WARN')
        return []

    records = []

    for line in rawsplits_str.split('\n'):
        if len(line) > 2:
            tmp = line.split('/')
            code = int(tmp[0].split(':')[1])

            if code == finish_code:
                card = int(tmp[0].split(':')[0])
                time = tmp[1]
                
                records.append(Record(card, code, time))

    return records

def get_finished_cards(window, qe_finish_filename):

    try:
        file = open(qe_finish_filename,"r")
        qe_finishes_str = file.read()
        file.close()

    except:
        window_terminal(window, 'Cannot read QE finish file', 'WARN')
        return []

    cards = []

    for line in qe_finishes_str.split('\n'):
        if len(line) > 2:
            tmp = line.split('/')
            card = int(tmp[0].split(':')[0])
            
            cards.append(card)

    return cards, qe_finishes_str

def update_finish(window, rawsplits_filename, bb_finish_filename, qe_finish_filename, finish_code):

    new_finishes = 0

    raw_finishes = get_finishes_from_rawsplits(window, rawsplits_filename, finish_code)
    
    finished_cards, qe_finishes_str = get_finished_cards(window, qe_finish_filename)

    finishes_str = qe_finishes_str

    for record in raw_finishes:
        if record.card not in finished_cards:
            new_finishes += 1
            newline = "{}: FIN/{}000/O.K.\n".format(str(record.card).rjust(8), record.time)
            finishes_str += newline

    try:
        file = open(bb_finish_filename,"w")
        file.write(finishes_str)
        file.close()

        if new_finishes:
            window_terminal(window, '{} unread finishes uploaded'.format(new_finishes))

    except:
        window_terminal(window, 'Cannot write to BB finish file', 'WARN')
        
    return new_finishes

def get_rawsplits(comp_id, last_punch):

    rawsplitsURL = "http://bluebox.oresults.eu/api/punch/rawsplits.php"

    response = requests.get(rawsplitsURL, json={"comp_id": comp_id, "last_punch": last_punch})

    last_punch = int(response.headers['last-punch'])

    rawsplits_str = response.text

    return rawsplits_str, last_punch

def update_rawsplits(window, comp_id, last_punch, filename):

    new_splits = 0

    rawsplits_str, new_last_punch = get_rawsplits(comp_id, last_punch)

    if last_punch == new_last_punch:
        return last_punch

    try:
        file = open(filename,"a+")
        file.write(rawsplits_str)
        file.close()

        new_splits = new_last_punch-last_punch

        window_terminal(window, '{} new splits received'.format(new_splits))

    except:
        window_terminal(window, 'Cannot write into rawsplits file', 'WARN')
        
    return new_last_punch

def update_settings_elements(window, disabled):
    
    window["-FILE-"].update(disabled=disabled)
    window["-QE-FINISH-"].update(disabled=disabled)
    window["-BB-FINISH-"].update(disabled=disabled)
    window["-REFRESH-TIME-"].update(disabled=disabled)
    window["-COMP-ID-"].update(disabled=disabled)
    window["-FINISH-CN-"].update(disabled=disabled)
    window["-LAST-PUNCH-"].update(disabled=disabled)

def window_terminal(window, text, type='INFO'):
    
    event, values = window.read(timeout=0)
    
    terminal_text = values["-TERMINAL-"]

    new_line = type + ': ' + text + '\n'

    window["-TERMINAL-"].update(new_line+terminal_text)

def main_window():

    filename = None
    refresh_t = 5
    comp_id = None
    last_punch = 0
    running = False
    finished = []
    finished_data = []

    DEFAULT_INFO_TEXT = " " * 60
    TERMINAL_TEXT = ""

    sg.theme('DarkBlue')

    RAWSPLITS_row = [
        sg.Text("RawSplits file:"),
        sg.In(size=(50, 1), enable_events=True, key="-FILE-"),
        sg.FileBrowse("..."),
    ]

    QE_finish_row = [
        sg.Text("QE finish file: "),
        sg.In(size=(50, 1), enable_events=True, key="-QE-FINISH-"),
        sg.FileBrowse("..."),
    ]

    BB_finish_row = [
        sg.Text("BB finish file: "),
        sg.In(size=(50, 1), enable_events=True, key="-BB-FINISH-"),
        sg.FileBrowse("..."),
    ]

    refresh_time_setter = [
        sg.Text("Bluebox comp. ID:"),
        sg.In(size=(4, 1), enable_events=True, key="-COMP-ID-"),
        sg.Text("        Finish CN:"),
        sg.Spin(initial_value=2, size=(4, 1), enable_events=True, key="-FINISH-CN-", values=[i for i in range(1, 300)]),
        sg.Text("        Refresh [s]:"),
        sg.Spin(initial_value=refresh_t, size=(4, 1), enable_events=True, key="-REFRESH-TIME-", values=[i for i in range(1, 60)])
    ]

    last_punch_row = [
        sg.Text("Last punch ID:"),
        sg.Spin(initial_value=0, size=(6, 1), enable_events=True, key="-LAST-PUNCH-", values=[i for i in range(1, 100000)])
    ]

    text_row = [
        sg.Text(" STOPPED ", key="-STATE-INDICATOR-", text_color=None, background_color='red'),
        sg.Text(DEFAULT_INFO_TEXT, key="-INFO-TEXT-", justification='c'),        
    ]

    terminal_row = [
        sg.Multiline(default_text=TERMINAL_TEXT, enable_events=True, key="-TERMINAL-", disabled=True,  size=(65, 15))
    ]

    action_button = [
        sg.Button(" START ", enable_events=True, key="-START-STOP-")
    ]

    layout = [refresh_time_setter, last_punch_row, RAWSPLITS_row, BB_finish_row, QE_finish_row, text_row, terminal_row, action_button]

    icon_path = None

    # Create the window
    window = sg.Window("Bluebox Connector", icon=icon_path, layout=layout, enable_close_attempted_event=True)

    # Create an event loop
    while True:
        event, values = window.read(timeout=0)

        if event in sg.WINDOW_CLOSE_ATTEMPTED_EVENT and not running:
            break

        if event == "-START-STOP-":
            
            running = not running
            start_time = time.time()
            if running:

                # TODO: Check of the values

                if not values["-FILE-"] or not values["-COMP-ID-"] or not values["-QE-FINISH-"]:
                    
                    running = not running

                    window["-INFO-TEXT-"].update("Missing values!", text_color='red')

                else:
                    rawsplits_filename = values["-FILE-"]
                    qe_finish_filename = values["-QE-FINISH-"]
                    bb_finish_filename = values["-BB-FINISH-"]
                    finish_code = values["-FINISH-CN-"]
                    refresh_t = int(values["-REFRESH-TIME-"])
                    comp_id = int(values["-COMP-ID-"])
                    last_punch = int(values["-LAST-PUNCH-"])

                    window["-START-STOP-"].update(" STOP ")
                    update_settings_elements(window, disabled=True)
                    window["-STATE-INDICATOR-"].update(" RUNNING ", text_color=None, background_color='green')

                    last_punch = update_rawsplits(window, comp_id=comp_id, last_punch=last_punch, filename=rawsplits_filename)
                    window["-LAST-PUNCH-"].update(value=last_punch)

                    update_finish(window, rawsplits_filename, bb_finish_filename, qe_finish_filename, finish_code)
            
            else:
                window["-START-STOP-"].update(" START ")
                update_settings_elements(window, disabled=False)
                window["-STATE-INDICATOR-"].update(" STOPPED ", text_color=None, background_color='red')

                window["-INFO-TEXT-"].update(DEFAULT_INFO_TEXT)
        
        if running:
            countdown = int(refresh_t - ((time.time()-start_time)%refresh_t)) + 1
            TIMER_TEXT = "Data refresh in " + str(countdown) + " s" 
            window["-INFO-TEXT-"].update(TIMER_TEXT, text_color='white')


        if running and (time.time()-start_time) > refresh_t:
            last_punch = update_rawsplits(window, comp_id=comp_id, last_punch=last_punch, filename=rawsplits_filename)
            window["-LAST-PUNCH-"].update(value=last_punch)

            update_finish(window, rawsplits_filename, bb_finish_filename, qe_finish_filename, finish_code)
            
            start_time = time.time()

    window.close()

if __name__ == "__main__":
    main_window()
    # sg.theme_previewer()
    # sg.preview_all_look_and_feel_themes()