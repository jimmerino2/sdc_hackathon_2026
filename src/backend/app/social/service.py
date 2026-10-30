"""Pollen and friends (profiles.total_pollen, table social_friendship; migration 0021). Friend requests are addressed
by email, since names are not unique and the person may not have an account yet."""
import re
from datetime import datetime, timezone

from fastapi import HTTPException
from supabase import Client

from app.social.schemas import Friend, Incoming, Player, Sent, Social

POLLEN_PER_STINGER = 500  # what a stinger is worth; the leaderboard ranks pollen
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PERSON = "profile_id,name,email,bee,total_pollen"


def add_pollen(db: Client, profile_id: str, amount: int) -> None:
    """Add pollen to a profile atomically. Best effort: a failure is logged, since the award it follows (a stinger)
    has already been saved."""
    try:
        db.rpc("add_pollen", {"p_profile_id": profile_id, "p_amount": amount}).execute()
    except Exception as e:
        print(f"Pollen not added for {profile_id} ({type(e).__name__}: {getattr(e, 'message', e)})")


def _hint(email: str) -> str:
    return f"{email.split('@')[0]}@..."


def _me(db: Client, profile_id: str) -> dict:
    rows = db.table("profiles").select(PERSON).eq("profile_id", profile_id).limit(1).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="No such profile.")
    return rows[0]


def _my_email(me: dict) -> str:
    return (me.get("email") or "").lower()


def _by_emails(db: Client, emails: list[str]) -> dict[str, dict]:
    """Profiles synced with these (lower-cased) emails, keyed by lower-cased email. Emails match in any case."""
    out: dict[str, dict] = {}
    for e in dict.fromkeys(emails):
        rows = db.table("profiles").select(PERSON).ilike("email", e.replace("%", r"\%").replace("_", r"\_")).limit(1).execute().data
        if rows:
            out[e] = rows[0]
    return out


def get_social(db: Client, profile_id: str) -> Social:
    me = _me(db, profile_id)
    email = _my_email(me)
    cols = "friendship_id,addressee_email,status,requester_id"
    sent_rows = db.table("social_friendship").select(cols).eq("requester_id", profile_id).execute().data
    inc_rows = db.table("social_friendship").select(cols).eq("addressee_email", email).execute().data if email else []

    requester_ids = sorted({r["requester_id"] for r in inc_rows})
    requesters = {p["profile_id"]: p for p in db.table("profiles").select(PERSON).in_("profile_id", requester_ids).execute().data} if requester_ids else {}
    addressees = _by_emails(db, [r["addressee_email"] for r in sent_rows])

    friends: list[Friend] = []
    people: list[dict] = [me]
    for r in sent_rows:
        p = addressees.get(r["addressee_email"])
        if r["status"] == "accepted" and p:
            friends.append(Friend(profile_id=p["profile_id"], name=p["name"], bee=p["bee"], email_hint=_hint(r["addressee_email"]), friendship_id=r["friendship_id"]))
            people.append(p)
    for r in inc_rows:
        p = requesters.get(r["requester_id"])
        if r["status"] == "accepted" and p:
            friends.append(Friend(profile_id=p["profile_id"], name=p["name"], bee=p["bee"], email_hint=_hint(p.get("email") or ""), friendship_id=r["friendship_id"]))
            people.append(p)

    ranked = sorted({p["profile_id"]: p for p in people}.values(), key=lambda p: (-p["total_pollen"], p["name"].lower()))
    board = [Player(profile_id=p["profile_id"], name=p["name"], bee=p["bee"], pollen=p["total_pollen"], rank=i, is_me=p["profile_id"] == profile_id)
             for i, p in enumerate(ranked, start=1)]
    return Social(
        pollen=me["total_pollen"],
        leaderboard=board,
        friends=sorted(friends, key=lambda f: f.name.lower()),
        incoming=[Incoming(friendship_id=r["friendship_id"], name=requesters[r["requester_id"]]["name"], bee=requesters[r["requester_id"]]["bee"], email=requesters[r["requester_id"]].get("email") or "")
                  for r in inc_rows if r["status"] == "pending" and r["requester_id"] in requesters],
        sent=[Sent(friendship_id=r["friendship_id"], email=r["addressee_email"], signed_up=r["addressee_email"] in addressees)
              for r in sent_rows if r["status"] == "pending"],
    )


def _accept(db: Client, friendship_id: str) -> None:
    db.table("social_friendship").update({"status": "accepted", "accepted_at": datetime.now(timezone.utc).isoformat()}).eq("friendship_id", friendship_id).execute()


def request_friend(db: Client, profile_id: str, email: str) -> Social:
    """Send a friend request to an email. If they already asked us, this accepts theirs instead. 422 for a bad email or
    your own, 409 if you are already friends or already asked, or if you have no email yet (accounts are tied to emails)."""
    email = email.strip().lower()
    if not EMAIL.match(email):
        raise HTTPException(status_code=422, detail="That doesn’t look like an email address.")
    mine = _my_email(_me(db, profile_id))
    if not mine:
        raise HTTPException(status_code=409, detail="Add your email to your profile first, so friends can find you.")
    if email == mine:
        raise HTTPException(status_code=422, detail="That’s your own email.")

    theirs = _by_emails(db, [email]).get(email)
    if theirs:  # did they already ask us?
        back = (db.table("social_friendship").select("friendship_id,status").eq("requester_id", theirs["profile_id"])
                .eq("addressee_email", mine).limit(1).execute().data)
        if back:
            if back[0]["status"] == "accepted":
                raise HTTPException(status_code=409, detail="You’re already friends.")
            _accept(db, back[0]["friendship_id"])
            return get_social(db, profile_id)
    existing = db.table("social_friendship").select("status").eq("requester_id", profile_id).eq("addressee_email", email).limit(1).execute().data
    if existing:
        raise HTTPException(status_code=409, detail="You’re already friends." if existing[0]["status"] == "accepted" else "You’ve already sent that request.")
    db.table("social_friendship").insert({"requester_id": profile_id, "addressee_email": email}).execute()
    return get_social(db, profile_id)


def _row(db: Client, friendship_id: str) -> dict:
    rows = db.table("social_friendship").select("friendship_id,requester_id,addressee_email,status").eq("friendship_id", friendship_id).limit(1).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="No such request.")
    return rows[0]


def accept(db: Client, profile_id: str, friendship_id: str) -> Social:
    """Accept a request addressed to this learner's email. 404 if it isn't theirs to accept."""
    row = _row(db, friendship_id)
    if row["addressee_email"] != _my_email(_me(db, profile_id)):
        raise HTTPException(status_code=404, detail="No such request.")
    if row["status"] == "pending":
        _accept(db, friendship_id)
    return get_social(db, profile_id)


def remove(db: Client, profile_id: str, friendship_id: str) -> Social:
    """Decline a request, cancel one you sent, or unfriend: delete the row, if this learner is on either side."""
    row = _row(db, friendship_id)
    if row["requester_id"] != profile_id and row["addressee_email"] != _my_email(_me(db, profile_id)):
        raise HTTPException(status_code=404, detail="No such request.")
    db.table("social_friendship").delete().eq("friendship_id", friendship_id).execute()
    return get_social(db, profile_id)
