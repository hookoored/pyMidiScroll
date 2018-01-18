"""
TODO: add more user control over animation (more options)
TODO: convert to python3
TODO: cleanup
TODO: pick colors more intelligently
TODO: include run-in file so video doesn't start immediately playing
technique: make two avis, one for the run-up and one that starts immediately. Then combine them.
mencoder -ovc lavc start.avi end.avi -o complete.avi

DONE:
*make it so that shorter notes appear on top of bigger ones so they're not hidden
technique: make a list of notes, sort them by duration, and then draw them all at once.
*autodetect mp3 length + higher precision
*autodetect highest/lowest note and set offsets appropriately

"""
import pygame
import random
import midi
from mido import MidiFile, second2tick
import Queue
import os


def getMP3Duration(mp3_file):
    mp3_file = mp3_file.replace(" ", "\\ ")
    x = os.popen("ffmpeg -i " + mp3_file + " 2>&1 | grep Duration")
    time = x.readline()
    print time
    time = time.split(" ")[3].split(":")
    time = float(time[0]) * 60 * 60 + float(time[1]) * 60 + float(time[2][:-1])
    return time


def get_note_lists(tracks, tpb):
    """
    Returns a list of lists of notes and the number of ticks. Each note is of the form
    [pitch,velocity,start_time,end_time]
    where start_time and end_time are in ticks (which has no relation to
    time or picture frames)

    Each track from the midi is represented as a different list of notes.
    """
    note_lists = []
    max_len = 0
    max_len2 = 0
    lowest_note = 9999
    highest_note = 0
    # Current tempo
    tempo = 500000
    # Time elapsed since beginning (in ticks)
    time_elapsed = 0
    for track in tracks:
        note_dic = {}
        # List of notes in the format listed above
        note_list = []
        for msg in track:
            # Change multiplier to be consistent with tempo
            if msg.type == 'set_tempo':
                tempo = msg.tempo

            if msg.type == 'note_on' or msg.type == 'note_off':
                # Delta time of message
                time = second2tick(msg.time, tpb, tempo) / 640
                if(time > max_len2):
                    max_len2 = time
                if(not msg.note in note_dic):
                    note_dic[msg.note] = [msg.velocity, time]
                else:
                    # Note in [pitch,velocity,start_time,end_time] format
                    note = [msg.note] + note_dic.pop(msg.note) + [time]

                    # Adjust timings with time_elapsed
                    note[2] += time_elapsed
                    note[3] += note[2]

                    # Update time_elapsed
                    time_elapsed = note[3]

                    # Add note to list
                    note_list += [note]
                    print(note[3] - note[2])
                if(time > max_len):
                    max_len = time
                if(msg.note < lowest_note):
                    lowest_note = msg.note
                if(msg.note > highest_note):
                    highest_note = msg.note
            if msg.type == "END_OF_TRACK":
                print msg
        note_lists += [note_list]
    print "max_len:", max_len, max_len2
    print 'nl', (max(max_len, max_len2), note_lists, lowest_note, highest_note, max_len)
    return (max(max_len, max_len2) * 6, note_lists, lowest_note, highest_note, max_len * 6)


def make_pictures(midi_file, mp3_file):
    mainloop, fps, screen_width, screen_height = True, 30., 800, 640
    offset = -screen_width
    song_duration = getMP3Duration(mp3_file)
    print song_duration
    pygame.init()

    screen = pygame.display.set_mode([screen_width, screen_height])
    screen.fill([0, 0, 0])

    Clock = pygame.time.Clock()
    m = MidiFile(midi_file)

    (max_len, note_lists, lowest_note, highest_note,
     end_note) = get_note_lists(m.tracks, m.ticks_per_beat)
    note_range = highest_note - lowest_note
    print (max_len, note_lists, lowest_note, highest_note,
     end_note)
    # the number of pixels difference for going up by 1 in pitch
    pitch_height = float(screen_height - 30) / note_range
    height_offset = screen_height + lowest_note * pitch_height - 15
    # print height_offset-highest_note*pitch_height

    # A decent hand-picked set of colors...
    colors = [
        (51, 255, 000),
        (51, 255, 255),
        (51, 000, 255),
        (153, 000, 255),
        (153, 051, 000),
        (204, 000, 000),
        (204, 000, 255),
        (153, 000, 000),
        (204, 000, 102),
        (204, 051, 204),
    ]
    colors = colors * 5  # in case there are a lot of tracks...
    colors = colors[:len(note_lists)]

    ticksPerPixel = float(max_len) / (fps * song_duration)
    print ticksPerPixel, "tpp"
    pygame.mixer.music.load(mp3_file)
    playing = False

    os.system("mkdir " + midi_file + "tmp1")
    os.system("mkdir " + midi_file + "tmp2")
    folder = midi_file + "tmp1"
    while mainloop:
        # Clock.tick(fps)
        pygame.display.set_caption("pyMidiScroll")
        screen.fill((0, 0, 0))

        i = 0
        rects = Queue.PriorityQueue()
        for notes in note_lists:
            # Put all of the rectangles we are going to draw into a priority queue
            # sorted by duration, so that shorter notes don't get covered
            # by longer ones when we draw them on the screen.
            for note in notes:
                rect = (note[2] / ticksPerPixel - offset,
                        height_offset - note[0] * pitch_height,
                        (note[3] - note[2]) / ticksPerPixel - 1,
                        2 + note[1] / (screen_height / 40))
                if(note[3] == end_note and rect[0] + rect[2] < screen_width / 2):
                    mainloop = False
                if(rect[0] > screen_width or rect[0] + rect[2] < 0):
                    continue
                # print "note: ", rect
                if(rect[0] <= screen_width / 2):
                    folder = midi_file + "tmp2"
                if(rect[0] <= screen_width / 2 and rect[0] + rect[2] >= screen_width / 2):
                    if(not playing):
                        # pygame.mixer.music.play(0,0)
                        playing = True
                    color = (255, 255, 255)
                else:
                    color = colors[i]
                # use duration as key
                rects.put((-rect[2], color, rect))
            i += 1
        while not rects.empty():
            rect = rects.get()
            # print rect[0], rects.qsize()
            pygame.draw.ellipse(screen, rect[1], rect[2])
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                mainloop = False  # Be IDLE friendly!
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    mainloop = False  # Be IDLE friendly!
        pygame.display.update()
        index = str(offset + screen_width)
        index = '0' * (10 - len(index)) + index
        pygame.image.save(screen, folder + "/frame" + index + ".jpeg")
        offset += 1
    print offset
    pygame.quit()  # Be IDLE friendly!


def makeMP3Fluid(midi_file, soundfont_file="~/soundfonts/SGM-V2.01.sf2"):
    os.system("fluidsynth -l -F fluid" + midi_file +
              ".wav " + soundfont_file + " " + midi_file)
    return "fluid" + midi_file + ".wav"


def makeMP3Timidity(midi_file):
    os.system("timidity " + midi_file + " -Ow -o " + midi_file + ".wav")
    return midi_file + ".wav"


def make_video(midi_file):
    mp3_file = makeMP3Fluid(midi_file)
    make_pictures(midi_file, mp3_file)
    mp3_file = makeMP3Timidity(midi_file)
    # make video of midi
    os.system("mencoder mf://" + midi_file + "tmp2/*.jpeg \
-mf w=400:h=320:fps=30:type=jpeg -ovc lavc -lavcopts \
vcodec=mpeg4:mbd=2:trell -oac copy -o tmp" + midi_file + ".avi")
    # add sound to midi video
    os.system("mencoder -ovc copy -audiofile " + mp3_file + "\
 -oac copy tmp" + midi_file + ".avi -o 0" + midi_file + ".avi")

    # make the video for the "run-in" (no music playing)
    # os.system("mencoder mf://"+midi_file+"tmp1/*.png \
#-mf w=400:h=320:fps=30:type=png -ovc lavc -lavcopts \
# vcodec=mpeg4:mbd=2:trell -oac copy -o tmpRunin"+midi_file+".avi")
    # add sound to run-in video
#    os.system("mencoder -ovc copy -audiofile silence.wav\
# -oac copy tmpRunin"+midi_file+".avi -o tmpRunin"+midi_file+".avi")

    # combine run-in and song
    #os.system("mencoder -oac copy -ovc copy tmpRunin"+midi_file+".avi "+midi_file+".avi -o FULL"+midi_file+".avi")
    return 1


from sys import argv
if len(argv) == 1:
    mid_file = raw_input("MIDI File: ")

else:
    mid_file = argv[1]

make_video(mid_file)

# Delete temp files

from shutil import rmtree
rmtree(mid_file + "tmp1")
rmtree(mid_file + "tmp2")

from os import remove
remove(mid_file + ".wav")
remove("fluid" + mid_file + ".wav")
remove("tmp" + mid_file + ".avi")
