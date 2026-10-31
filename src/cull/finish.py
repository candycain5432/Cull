# Acts on a finished review: rejects go to the Trash and picks move to their own folder. The browser asks first
import shutil
from threading import Lock
from send2trash import send2trash
from cull.folders import target_for
from cull.review import readable

WANTED = {"delete": "reject", "move": "pick"} # The decision a photo needs before each action can touch it
one_at_a_time = Lock()


class DecisionsChanged(Exception):
    pass


# Beside the shoot like the group folders, or the next run would scan the picks all over again
def picks_folder(folder, settings):
    folder = folder.resolve()
    return folder.with_name(folder.name + settings.picks_suffix)


def move_pick(file, name, picks):
    picks.mkdir(exist_ok=True)
    shutil.move(file, target_for(picks, name)) # Picks the name itself, so this can't overwrite an earlier pick


# Takes id to name for the photos the photographer confirmed, one that fails stays where it is with its decision
def finish(shoot, decisions, action, names, picks):
    with one_at_a_time:
        # Every photo is checked before any is touched, so a stale page can't act on the wrong files
        if any(decisions.saved.get(name) != WANTED[action] for name in names.values()):
            raise DecisionsChanged("Your decisions have changed, reload the page and try again")

        done, failed = [], []
        for number, name in names.items():
            file = shoot.folder / name
            try:
                if action == "delete":
                    send2trash(file)
                else:
                    move_pick(file, name, picks)
                done.append(number)
            except FileNotFoundError:
                failed.append({"name": readable(name), "reason": "it's no longer in the shoot folder"})
            except OSError as e: # Never falls back to deleting for good, the photo just stays
                failed.append({"name": readable(name), "reason": e.strerror or str(e)})

        shoot.finished[action] += len(done)
        shoot.drop(done, picked=action == "move")
        # A new photo with the same name must not inherit this decision
        decisions.apply([(names[number], None) for number in done])

    return {"done": len(done), "failed": failed}
