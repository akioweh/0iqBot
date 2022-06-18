from typing import Iterable

from discord import Activity, ActivityType, CustomActivity, Game, Member, Role, Spotify, Streaming


def member_details(m: Member):
    return f"**Server Joined:** `{m.joined_at.strftime('%d/%m/%Y, %H:%M:%S') if m.joined_at else 'N/A'}` \n" \
           f"**Current Activities:** `{activity_details(m.activities) if m.activities else 'N/A'}` \n" \
           f"**Current Server:** `{m.guild.name if hasattr(m, 'guild') else 'N/A'}` \n" \
           f"**Nick Name:** `{getattr(m, 'nick', 'N/A')}` \n" \
           f"**Pending Member Verification:** `{getattr(m, 'pending', 'N/A')}` \n" \
           f"**Server Boosting Since:** `{m.premium_since.strftime('%d/%m/%Y, %H:%M:%S') if m.premium_since else 'N/A'}` \n" \
           f"**Recent Messages:** TODO \n" \
           f"**Raw Status:** `{getattr(m, 'raw_status', 'N/A')}` \n" \
           f"**Online Status (mobile):** `{getattr(m, 'mobile_status', 'N/A')}` \n" \
           f"**Online Status (desktop):** `{getattr(m, 'desktop_status', 'N/A')}` \n" \
           f"**Online Status (web):** `{getattr(m, 'web_status', 'N/A')}` \n" \
           f"**On Mobile:** `{m.is_on_mobile()}` \n" \
           f"**Render Color:** `{getattr(m, 'color', 'N/A')}` \n" \
           f"**Roles:** `{role_names(m.roles) if hasattr(m, 'roles') else 'N/A'}` \n" \
           f"**Mention String:** `{getattr(m, 'mention', 'N/A')}` \n" \
           f"**Display Name:** `{getattr(m, 'display_name', 'N/A')}` \n" \
           f"**Current Activity:** `{getattr(m, 'activity', 'N/A')}` \n" \
           f"**Highest Role:** `{getattr(m, 'top_role', 'N/A')}` \n" \
           f"**Server Permissions:** TODO \n" \
           f"**Voice State:** TODO \n" \
           f"**Avatar URL:** `{getattr(m, 'avatar_url', 'N/A')}` \n" \
           f"**Bot Account:** `{getattr(m, 'bot', 'N/A')}` \n" \
           f"**Account Created:** `{m.created_at.strftime('%d/%m/%Y, %H:%M:%S') if hasattr(m, 'created_at') else 'N/A'}` \n" \
           f"**DM Channel:** `{getattr(m, 'dm_channel', 'N/A')}` \n" \
           f"**User ID:** `{getattr(m, 'id', 'N/A')}` \n" \
           f"**Animated Avatar:** `{m.is_avatar_animated()}` \n" \
           f"**Public Badges:** `{badge_names(m.public_flags) if hasattr(m, 'public_flags') else 'N/A'}` \n" \
           f"**Official Account:** `{getattr(m, 'system', 'N/A')}` \n"


def activity_details(activities: Iterable[Activity] | Activity) -> str:
    act_str = ''
    activities = list(activities) if not type(activities, Iterable) else activities
    for activity in activities:
        if isinstance(activity, Game):
            act_str += f'- Playing {activity.name}{(" since " + activity.start.strftime("%d/%m/%Y, %H:%M:%S")) if activity.start else ""} \n'
        elif isinstance(activity, Streaming):
            act_str += f'- Streaming{(" " + activity.game) if activity.game else ""} on {activity.platform}{(" :" + activity.name) if activity.name else ""} \n'
        elif isinstance(activity, CustomActivity):
            act_str += f'- Custom status: {activity.emoji if activity.emoji else ""} {activity.name}'
        elif isinstance(activity, Activity):
            act_str += _generic_activity_details(activity)
        elif isinstance(activity, Spotify):
            act_str += f'- Listening to {activity.title} by {activity.artist} on Spotify \n'
        else:
            act_str += '- Unknown Activity \n'
    return act_str.rstrip('\n')


def badge_names(flags) -> str:
    names = ('- Discord Staff \n' if flags.staff else '') + \
            ('- Discord Partner \n' if flags.partner else '') + \
            ('- Hypesquade Host \n' if flags.hypesquad else '') + \
            ('- Bug Hunter lvl1 \n' if flags.bug_hunter else '') + \
            ('- Bug Hunter lvl2 \n' if flags.bug_hunter_level_2 else '') + \
            ('- Hypesquad House: Bravery \n' if flags.hypesquad_bravery else '') + \
            ('- Hypesquad House: Brilliance \n' if flags.hypesquad_brilliance else '') + \
            ('- Hypesquad House: Balance \n' if flags.hypesquad_balance else '') + \
            ('- Early Supporter \n' if flags.early_supporter else '') + \
            ('- Team User \n' if flags.team_user else '') + \
            ('- System User \n' if flags.system else '') + \
            ('- Verified Bot \n' if flags.verified_bot else '') + \
            ('- Early Bot Developer' if flags.early_verified_bot_developer else '')
    return names


def role_names(roles: list[Role]) -> str:
    return ' \n'.join(['- ' + str(role) for role in roles])


def _generic_activity_details(activity: Activity) -> str:
    act_str = f'{activity.name} | {activity.details} | {activity.details} '
    act_str += (' since ' + activity.start.strftime('%d/%m/%Y, %H:%M:%S')) if activity.start else ''
    if activity.type == ActivityType.playing:
        return f'Playing ' + act_str
    elif activity.type == ActivityType.streaming:
        return f'Streaming ' + act_str
    elif activity.type == ActivityType.listening:
        return f'Listening to ' + act_str
    elif activity.type == ActivityType.watching:
        return 'Watching ' + act_str
    elif activity.type == ActivityType.competing:
        return 'Competing in ' + act_str
    elif activity.type == ActivityType.custom:
        return 'Custom: ' + act_str
    elif activity.type == ActivityType.unknown:
        return 'Unknow Activity'
    else:
        return ''


__all__ = ['member_details', 'activity_details', 'badge_names', 'role_names']
