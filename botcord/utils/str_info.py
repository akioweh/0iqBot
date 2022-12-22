"""Functions to generated formatted strings
containing information about Discord objects"""

from discord import (Activity,
                     ActivityType,
                     BaseActivity,
                     CustomActivity,
                     Game,
                     Member,
                     PublicUserFlags,
                     Role,
                     Spotify,
                     Streaming)


def member_details(m: Member) -> str:
    """Gives you more info about a member than what the CIA has on them,
    all while formatting everything nicely :)"""
    return f"**`{m.name}`#`{m.discriminator}`** (`{m.id}`) \n" \
           f"**Bot Account:** `{getattr(m, 'bot', 'N/A')}` \n" \
           f"**Official Account:** `{getattr(m, 'system', 'N/A')}` \n" \
           f"**Created At:** {m.created_at.strftime('%d/%m/%Y, %H:%M:%S') if m.created_at else 'N/A'} \n" \
           f"**Server Joined:** `{m.joined_at.strftime('%d/%m/%Y, %H:%M:%S') if m.joined_at else 'N/A'}` \n" \
           f"**Current Activities:** \n```\n{activity_details(*m.activities) if m.activities else 'N/A'}\n``` \n" \
           f"**Current Server:** `{m.guild.name if hasattr(m, 'guild') else 'N/A'}` \n" \
           f"**Nick Name:** `{getattr(m, 'nick', 'N/A')}` \n" \
           f"**Pending Member Verification:** `{getattr(m, 'pending', 'N/A')}` \n" \
           f"**Server Boosting Since:** `{m.premium_since.strftime('%d/%m/%Y, %H:%M:%S') if m.premium_since else 'N/A'}` \n" \
           f"**Timed-out Until:** `{m.timed_out_until.strftime('%d/%m/%Y, %H:%M:%S') if m.timed_out_until else 'N/A'}` \n" \
           f"**Recent Messages:** TODO \n" \
           f"**Raw Status:** `{getattr(m, 'raw_status', 'N/A')}` " \
           f"**(mobile):** `{getattr(m, 'mobile_status', 'N/A')}` " \
           f"**(desktop):** `{getattr(m, 'desktop_status', 'N/A')}` " \
           f"**(web):** `{getattr(m, 'web_status', 'N/A')}` \n" \
           f"**On Mobile:** `{m.is_on_mobile()}` \n" \
           f"**Render Color:** `{getattr(m, 'color', 'N/A')}` \n" \
           f"**Roles:** \n```\n{role_names(*m.roles) if hasattr(m, 'roles') else 'N/A'}\n``` \n" \
           f"**Mention String:** `{getattr(m, 'mention', 'N/A')}` \n" \
           f"**Display Name:** `{getattr(m, 'display_name', 'N/A')}` \n" \
           f"**Current Activity:** `{getattr(m, 'activity', 'N/A')}` \n" \
           f"**Highest Role:** `{getattr(m, 'top_role', 'N/A')}` \n" \
           f"**Server Permissions:** TODO \n" \
           f"**Voice State:** TODO \n" \
           f"**Avatar URL:** `{getattr(m, 'avatar_url', 'N/A')}` \n" \
           f"**Account Created:** `{m.created_at.strftime('%d/%m/%Y, %H:%M:%S') if hasattr(m, 'created_at') else 'N/A'}` \n" \
           f"**DM Channel:** `{getattr(m, 'dm_channel', 'N/A')}` \n" \
           f"**User ID:** `{getattr(m, 'id', 'N/A')}` \n" \
           f"**Animated Avatar:** `{m.avatar.is_animated()}` \n" \
           f"**Public Badges:** \n```\n{badge_names(m.public_flags) if hasattr(m, 'public_flags') else 'N/A'}\n``` \n"


def activity_details(*activities: BaseActivity) -> str:
    """Generates a highly sentient string describing the activities...
    figure the details out yourself :P"""
    act_str = ''
    for activity in activities:
        if isinstance(activity, Game):
            act_str += f'- Playing' \
                       f'{f" {activity.name}" if activity.name else ""}' \
                       f'{(" since " + activity.start.strftime("%d/%m/%Y, %H:%M:%S")) if activity.start else ""} \n'

        elif isinstance(activity, Streaming):
            act_str += f'- Streaming' \
                       f'{f" {activity.game}" if activity.game else ""}' \
                       f'{f" on {activity.platform}" if activity.platform else ""}' \
                       f'{f": {activity.name}" if activity.name else ""}' \
                       f'{f" at {activity.url}" if activity.url else ""} \n'

        elif isinstance(activity, CustomActivity):
            act_str += f'- Custom status: {(str(activity.emoji) + " ") if activity.emoji else ""}{activity.name} \n'

        elif isinstance(activity, Spotify):
            act_str += f'- Listening to {activity.title} by {activity.artist} on Spotify \n'

        elif isinstance(activity, Activity):
            act_str += _generic_activity_details(activity) + '\n'

        else:
            act_str += '- Unknown Activity \n'

    return act_str.strip()


def badge_names(flags: PublicUserFlags) -> str:
    """Generates a list of the names of the badges,
    delimited by newlines and prefixed by "- ";
    in the format of:

    ``- <badge name>``\n
    ``- <badge name>``\n
    ``- <badge name>``\n
    etc."""
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


def role_names(*roles: Role) -> str:
    """Generates a list of the names of the roles,
    separated by newlines and prefixed by "- ";
    in the format of:

    ``- <role name>``\n
    ``- <role name>``\n
    ``- <role name>``\n
    etc."""
    return ' \n'.join(('- ' + str(role) for role in roles))


def _generic_activity_details(activity: Activity) -> str:
    """Captures most of the activity details and
    returns them as a nicely formatted string"""
    act_str = ''
    if activity.created_at:
        act_str += f'{activity.created_at.strftime("%d/%m/%Y, %H:%M:%S")}: '
    if activity.emoji:
        act_str += f'{activity.emoji} '
    if activity.state:
        act_str += f'[{activity.state}] '

    match activity.type:
        case ActivityType.playing:
            act_str += 'Playing '
        case ActivityType.streaming:
            act_str += 'Streaming '
        case ActivityType.listening:
            act_str += 'Listening to '
        case ActivityType.watching:
            act_str += 'Watching '
        case ActivityType.custom:
            pass
        case ActivityType.competing:
            act_str += 'Competing in '
        case _:
            act_str += 'Unknown Activity '

    if activity.name:
        act_str += f'{activity.name} '
    if activity.start:
        act_str += f'since {activity.start.strftime("%d/%m/%Y, %H:%M:%S")} '
    if activity.details and activity.details != activity.name:
        act_str += f'({activity.details}) '
    if isinstance(activity, Streaming):
        if activity.platform:
            act_str += f'on {activity.platform} '
        if activity.url:
            act_str += f'at {activity.url} '

    return act_str.strip()


__all__ = ['member_details', 'activity_details', 'badge_names', 'role_names']
