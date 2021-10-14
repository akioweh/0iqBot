from typing import Iterable

from discord import Spotify, Activity, Game, Streaming, CustomActivity, ActivityType


async def member_details(member):
    return f"**Server Joined:** `{member.joined_at.strftime('%d/%m/%Y, %H:%M:%S') if member.joined_at else 'N/A'}` \n" \
           f"**Current Activities:** `{activity_names(member.activities) if member.activities else 'N/A'}` \n" \
           f"**Current Server:** `{member.guild.name if hasattr(member, 'guild') else 'N/A'}` \n" \
           f"**Nick Name:** `{getattr(member, 'nick', 'N/A')}` \n" \
           f"**Pending Member Verification:** `{getattr(member, 'pending', 'N/A')}` \n" \
           f"**Server Boosting Since:** `{member.premium_since.strftime('%d/%m/%Y, %H:%M:%S') if member.premium_since else 'N/A'}` \n" \
           f"**Recent Messages:** TODO \n" \
           f"**Raw Status:** `{getattr(member, 'raw_status', 'N/A')}` \n" \
           f"**Online Status (mobile):** `{getattr(member, 'mobile_status', 'N/A')}` \n" \
           f"**Online Status (desktop):** `{getattr(member, 'desktop_status', 'N/A')}` \n" \
           f"**Online Status (web):** `{getattr(member, 'web_status', 'N/A')}` \n" \
           f"**On Mobile:** `{member.is_on_mobile()}` \n" \
           f"**Render Color:** `{getattr(member, 'color', 'N/A')}` \n" \
           f"**Roles:** `{role_names(member.roles) if hasattr(member, 'roles') else 'N/A'}` \n" \
           f"**Mention String:** `{getattr(member, 'mention', 'N/A')}` \n" \
           f"**Display Name:** `{getattr(member, 'display_name', 'N/A')}` \n" \
           f"**Current Activity:** `{getattr(member, 'activity', 'N/A')}` \n" \
           f"**Highest Role:** `{getattr(member, 'top_role', 'N/A')}` \n" \
           f"**Server Permissions:** TODO \n" \
           f"**Voice State:** TODO \n" \
           f"**Avatar URL:** `{getattr(member, 'avatar_url', 'N/A')}` \n" \
           f"**Bot Account:** `{getattr(member, 'bot', 'N/A')}` \n" \
           f"**Account Created:** `{member.created_at.strftime('%d/%m/%Y, %H:%M:%S') if hasattr(member, 'created_at') else 'N/A'}` \n" \
           f"**DM Channel:** `{getattr(member, 'dm_channel', 'N/A')}` \n" \
           f"**User ID:** `{getattr(member, 'id', 'N/A')}` \n" \
           f"**Animated Avatar:** `{member.is_avatar_animated()}` \n" \
           f"**Public Badges:** `{badge_names(member.public_flags) if hasattr(member, 'public_flags') else 'N/A'}` \n" \
           f"**Official Account:** `{getattr(member, 'system', 'N/A')}` \n"


async def activity_names(activities):
    _act_str = ''
    activities = list(activities) if not type(activities, Iterable) else activities
    for activity in activities:
        if isinstance(activity, Game):
            _act_str += f'- Playing {activity.name}{(" since " + activity.start.strftime("%d/%m/%Y, %H:%M:%S")) if activity.start else ""} \n'
        elif isinstance(activity, Streaming):
            _act_str += f'- Streaming{(" " + activity.game) if activity.game else ""} on {activity.platform}{(" :" + activity.name) if activity.name else ""} \n'
        elif isinstance(activity, CustomActivity):
            _act_str += f'- Custom status: {activity.emoji if activity.emoji else ""} {activity.name}'
        elif isinstance(activity, Activity):
            _act_str += await _activity_details(activity)
        elif isinstance(activity, Spotify):
            _act_str += f'- Listening to {activity.title} by {activity.artist} on Spotify \n'
        else:
            _act_str += '- Unknown Activity \n'
    return _act_str.rstrip('\n')


async def badge_names(flags):
    names = '- Discord Staff \n' if flags.staff else '' + \
            '- Discord Partner \n' if flags.partner else '' + \
            '- Hypesquade Host \n' if flags.hypesquad else '' + \
            '- Bug Hunter lvl1 \n' if flags.bug_hunter else '' + \
            '- Bug Hunter lvl2 \n' if flags.bug_hunter_level_2 else '' + \
            '- Hypesquad House: Bravery \n' if flags.hypesquad_bravery else '' + \
            '- Hypesquad House: Brilliance \n' if flags.hypesquad_brilliance else '' + \
            '- Hypesquad House: Balance \n' if flags.hypesquad_balance else '' + \
            '- Early Supporter \n' if flags.early_supporter else '' + \
            '- Team User \n' if flags.team_user else '' + \
            '- System User \n' if flags.system else '' + \
            '- Verified Bot \n' if flags.verified_bot else '' + \
            '- Early Bot Developer' if flags.early_verified_bot_developer else ''
    return names


async def role_names(roles):
    return ' \n'.join(['- ' + str(role) for role in roles])


async def _activity_details(activity):
    if not isinstance(activity, Activity):
        return None
    _act_str = f'{activity.name} | {activity.details} | {activity.details} {(" since " + activity.start.strftime("%d/%m/%Y, %H:%M:%S")) if activity.start else ""}'
    if activity.type == ActivityType.playing:
        return f'Playing ' + _act_str
    elif activity.type == ActivityType.streaming:
        return f'Streaming ' + _act_str
    elif activity.type == ActivityType.listening:
        return f'Listening to ' + _act_str
    elif activity.type == ActivityType.watching:
        return 'Watching ' + _act_str
    elif activity.type == ActivityType.competing:
        return 'Competing in ' + _act_str
    elif activity.type == ActivityType.custom:
        return 'Custom: ' + _act_str
    elif activity.type == ActivityType.unknown:
        return 'Unknow Activity'
    else:
        return ''

# End
