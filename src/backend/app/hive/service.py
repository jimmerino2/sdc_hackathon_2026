"""Protect the Hive (tables hive_*, stinger_award.spent_at; migration 0022): a lobby fights Robbee, each stinger spent
takes 20% of his HP and pays 500 pollen, a kill pays 1,000 to each member who stung that round, and friends can
invite each other into a party of up to 4. The multi-step changes run in SQL functions, so they are atomic."""
from fastapi import HTTPException
from supabase import Client

from app.hive.schemas import Event, Fight, Hive, Invitable, Invite, Member, Outgoing, PartyBee, Reward, StingResult
from app.social import service as social

DAMAGE = 20            # HP a sting takes off Robbee
STING_POLLEN = 500     # paid to whoever stings
KILL_POLLEN = 1000     # paid to each member who stung that round, on the kill
MAX_PARTY = 4
STINGS_TO_KILL = 100 // DAMAGE
FEED = 8               # "Recent hits" shown
PERSON = "profile_id,name,bee"

# What the SQL functions raise (their message) -> what the learner is told.
ERRORS = {
    "no_stinger": (409, "You’re out of stingers. Pass a challenge stage to earn one."),
    "no_invite": (404, "That invite isn’t valid any more."),
    "party_full": (409, "That party is full."),
}


def _rpc(db: Client, fn: str, args: dict):
    try:
        return db.rpc(fn, args).execute().data
    except Exception as e:
        for key, (status, message) in ERRORS.items():
            if key in str(getattr(e, "message", "")) or key in str(e):
                raise HTTPException(status_code=status, detail=message) from e
        print(f"hive: {fn} failed ({type(e).__name__}: {getattr(e, 'message', e)})")
        raise HTTPException(status_code=502, detail="The hive didn’t answer. Try again in a moment.") from e


def _people(db: Client, ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    return {p["profile_id"]: p for p in db.table("profiles").select(PERSON).in_("profile_id", sorted(set(ids))).execute().data}


def get_hive(db: Client, profile_id: str) -> Hive:
    """Everything the page shows: the lobby, the party, available stingers, invites, the feed and any popup due."""
    fight_id = _rpc(db, "hive_ensure", {"p_profile": profile_id})
    fight = db.table("hive_fight").select("fight_id,hp,kills").eq("fight_id", fight_id).limit(1).execute().data[0]
    member_rows = db.table("hive_member").select("profile_id,stings,joined_at").eq("fight_id", fight_id).order("joined_at").execute().data
    sent = db.table("hive_invite").select("invite_id,from_id,to_id,fight_id").eq("fight_id", fight_id).execute().data
    incoming = db.table("hive_invite").select("invite_id,from_id,fight_id").eq("to_id", profile_id).order("created_at").execute().data
    events = (db.table("hive_event").select("event_id,kind,profile_id,pollen,created_at,roadmap_challenge(title)")
              .or_(f"fight_id.eq.{fight_id},and(profile_id.eq.{profile_id},kind.eq.twist)")
              .order("created_at", desc=True).limit(FEED).execute().data)
    reward = (db.table("hive_reward").select("reward_id,pollen,round,party").eq("profile_id", profile_id).eq("seen", False)
              .order("created_at").limit(1).execute().data)
    available = db.table("stinger_award").select("challenge_id", count="exact").eq("profile_id", profile_id).is_("spent_at", "null").execute().count or 0
    friends = social.get_social(db, profile_id).friends

    people = _people(db, [m["profile_id"] for m in member_rows] + [i["to_id"] for i in sent] + [i["from_id"] for i in incoming]
                     + [e["profile_id"] for e in events])
    me = social._me(db, profile_id)
    in_party = {m["profile_id"] for m in member_rows}
    invited = {i["to_id"] for i in sent}

    # How big each inviting party is, and how hurt its Robbee.
    from_fights = sorted({i["fight_id"] for i in incoming})
    sizes: dict[str, int] = {}
    hp_of: dict[str, int] = {}
    if from_fights:
        for r in db.table("hive_member").select("fight_id").in_("fight_id", from_fights).execute().data:
            sizes[r["fight_id"]] = sizes.get(r["fight_id"], 0) + 1
        hp_of = {r["fight_id"]: r["hp"] for r in db.table("hive_fight").select("fight_id,hp").in_("fight_id", from_fights).execute().data}

    return Hive(
        fight=Fight(fight_id=fight["fight_id"], hp=fight["hp"], kills=fight["kills"], stings_dealt=(100 - fight["hp"]) // DAMAGE,
                    stings_to_kill=STINGS_TO_KILL, max_party=MAX_PARTY),
        members=[Member(profile_id=m["profile_id"], name=people[m["profile_id"]]["name"], bee=people[m["profile_id"]]["bee"],
                        stings=m["stings"], is_me=m["profile_id"] == profile_id) for m in member_rows if m["profile_id"] in people],
        stingers_available=available,
        pollen=me["total_pollen"],
        invites=[Invite(invite_id=i["invite_id"], from_name=people[i["from_id"]]["name"], from_bee=people[i["from_id"]]["bee"],
                        party_size=sizes.get(i["fight_id"], 0), hp=hp_of.get(i["fight_id"], 100))
                 for i in incoming if i["from_id"] in people and sizes.get(i["fight_id"], 0) > 0],
        outgoing=[Outgoing(invite_id=i["invite_id"], profile_id=i["to_id"], name=people[i["to_id"]]["name"], bee=people[i["to_id"]]["bee"])
                  for i in sent if i["to_id"] in people],
        invitable=[Invitable(profile_id=f.profile_id, name=f.name, bee=f.bee) for f in friends if f.profile_id not in in_party and f.profile_id not in invited],
        events=[Event(event_id=e["event_id"], kind=e["kind"], profile_id=e["profile_id"], name=(people.get(e["profile_id"]) or {}).get("name", "Someone"),
                      is_me=e["profile_id"] == profile_id, challenge_title=(e.get("roadmap_challenge") or {}).get("title"),
                      pollen=e["pollen"], created_at=e["created_at"]) for e in events],
        reward=Reward(reward_id=reward[0]["reward_id"], pollen=reward[0]["pollen"], round=reward[0]["round"],
                      party=[PartyBee(name=p["name"], bee=p["bee"]) for p in reward[0]["party"]]) if reward else None,
    )


def sting(db: Client, profile_id: str) -> StingResult:
    """Spend one stinger on Robbee. 409 if the learner has none."""
    out = _rpc(db, "hive_sting", {"p_profile": profile_id, "p_damage": DAMAGE, "p_pollen": STING_POLLEN, "p_kill_pollen": KILL_POLLEN})
    return StingResult(hive=get_hive(db, profile_id), defeated=out["defeated"], pollen=out["pollen"], kill_pollen=out["kill_pollen"])


def invite(db: Client, profile_id: str, to_id: str) -> Hive:
    """Invite a friend to the party. 422 if they aren't a friend, 409 if the party is full or they are already in it or
    already invited."""
    fight_id = _rpc(db, "hive_ensure", {"p_profile": profile_id})
    members = {m["profile_id"] for m in db.table("hive_member").select("profile_id").eq("fight_id", fight_id).execute().data}
    if len(members) >= MAX_PARTY:
        raise HTTPException(status_code=409, detail="Your party is full.")
    if to_id not in {f.profile_id for f in social.get_social(db, profile_id).friends}:
        raise HTTPException(status_code=422, detail="You can only invite friends.")
    if to_id in members:
        raise HTTPException(status_code=409, detail="They’re already in your party.")
    try:
        db.table("hive_invite").insert({"fight_id": fight_id, "from_id": profile_id, "to_id": to_id}).execute()
    except Exception as e:
        if getattr(e, "code", None) == "23505":
            raise HTTPException(status_code=409, detail="You’ve already invited them.") from e
        raise HTTPException(status_code=502, detail="The invite didn’t go through. Try again in a moment.") from e
    return get_hive(db, profile_id)


def accept(db: Client, profile_id: str, invite_id: str) -> Hive:
    """Join the inviting party, replacing the learner's current fight. 404 if the invite isn't theirs or is gone,
    409 if the party filled up."""
    _rpc(db, "hive_join", {"p_profile": profile_id, "p_invite": invite_id, "p_max": MAX_PARTY})
    return get_hive(db, profile_id)


def remove_invite(db: Client, profile_id: str, invite_id: str) -> Hive:
    """Decline an invite, or cancel one the party sent. 404 unless the learner is the invitee or in the inviting party."""
    rows = db.table("hive_invite").select("invite_id,to_id,fight_id").eq("invite_id", invite_id).limit(1).execute().data
    if rows:
        mine = db.table("hive_member").select("fight_id").eq("profile_id", profile_id).limit(1).execute().data
        if rows[0]["to_id"] != profile_id and not (mine and mine[0]["fight_id"] == rows[0]["fight_id"]):
            rows = []
    if not rows:
        raise HTTPException(status_code=404, detail="No such invite.")
    db.table("hive_invite").delete().eq("invite_id", invite_id).execute()
    return get_hive(db, profile_id)


def leave(db: Client, profile_id: str) -> Hive:
    """Leave the party for a fresh solo fight."""
    _rpc(db, "hive_leave", {"p_profile": profile_id})
    return get_hive(db, profile_id)


def reward_seen(db: Client, profile_id: str, reward_id: str) -> Hive:
    """Dismiss a kill popup."""
    db.table("hive_reward").update({"seen": True}).eq("reward_id", reward_id).eq("profile_id", profile_id).execute()
    return get_hive(db, profile_id)


def log_twist(db: Client, profile_id: str, challenge_id: str) -> None:
    """Note in the feed that Robbee rewrote a challenge brief. Best effort: the rewrite has already been saved."""
    try:
        mine = db.table("hive_member").select("fight_id").eq("profile_id", profile_id).limit(1).execute().data
        db.table("hive_event").insert({"fight_id": mine[0]["fight_id"] if mine else None, "profile_id": profile_id,
                                       "kind": "twist", "challenge_id": challenge_id}).execute()
    except Exception as e:
        print(f"hive: twist not logged for {challenge_id} ({type(e).__name__}: {getattr(e, 'message', e)})")
