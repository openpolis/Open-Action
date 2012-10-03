from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.urlresolvers import reverse

from askbot.models import Post, User
from askbot.models.repute import Vote
from askbot.models.user import Activity
from notification import models as notification
from action.models import Action
from action.signals import post_action_status_update, post_declared_vote_add 
from action_request.signals import action_moderation_request_submitted, action_moderation_request_processed
from action_request.models import ActionRequest
from oa_notification import consts as notification_consts
from action import const as action_consts
from askbot_extensions import consts as ae_consts

import logging

log = logging.getLogger(settings.PROJECT_NAME)


@receiver(post_save, sender=Post)
def notify_add_blog_post(sender, **kwargs):
    """ Notify to Action referrers and followers that a new post 
    has been added to the Action blog

    #1 set the recipients (the receivers)
    #2 send notification(notification.send)
    
    Possible options:
    * 'now=True and queue=True': error
    * 'now=True and queue=False': send notice immediately by passing 'now=True' to 
    send function
    * 'queue=True and now=False': queue the notice in order to send it later
    * 'now=False and queue=False'(default): let the default notification 
    configuration decide

    QUESTION: should we pass the referrer who created the blog post as the 
    sender of the notice (in sender=)?
    ANSWER: no, the sender is always "the system"
    """

    if kwargs['created']:
        post = kwargs['instance']

        # This is a generic Post post_save handler, 
        # so we have to check if it is an answer
        if post.is_answer():

            action = post.action

            referrers = action.referrers
            #WAS: followers = action.thread.followed_by.all()
            followers = action.followers
            # recipients
            users = referrers | followers

            extra_context = ({
                "blog_post" : post,
                "action" : action
            })

            notification.send(users=users, 
                label=notification_consts.ACTION_MAKE_BLOGPOST, 
                extra_context=extra_context, 
                on_site=True, 
                sender=None, 
                now=True
            )

#WAS: @receiver(post_save, sender=Vote)
@receiver(post_declared_vote_add, sender=Vote)
def notify_user_join_your_action(sender, **kwargs):
    """ Notify to the users who woted an Action that 
    another User has voted it. """
    log.debug("notify_user_join_same_action %s %s" % (sender, kwargs))

    #WAS: if kwargs['created']:
    vote = kwargs['vote_instance']
    post = vote.voted_post
    action = post.action

    if post.is_question():
        voter = vote.user

        extra_context = ({
            "user" : voter,
            "action" : action 
        })
        #recipients
        users = action.referrers

        #print "\nnotification.send users %s\n" % users
        notification.send(users=users, 
            label="user_join_your_action",
            extra_context=extra_context,
            on_site=True, 
            sender=None, 
            now=True
        )

@receiver(post_save, sender=Post)
def notify_user_comment_your_action(sender, **kwargs):
    """ Notify that a user commented an Action to its owners """

    if kwargs['created']:
        post = kwargs['instance']

        if post.is_comment_to_action():
            commenter = post.author
            action = post.action

            extra_content = ({
                "user" : commenter,
                "action" : action
            }) 
            #recipients
            users = post.action.referrers

            notification.send(users=users,
                label="user_comment_your_action",
                extra_context=extra_context,
                on_site=True, 
                sender=None, 
                now=True
            )

#WAS: @receiver(action_get_level_step, sender=Action)
@receiver(post_action_status_update, sender=Action)
def notify_post_status_update(sender, **kwargs):
    """ Notify two events:

    * a joined action reached a level step: this is notified 
    to the voters of the Action;
    * a favourite topic action reached a level step: this is
    notified to the user who are not voters of the Action,
    but are voters of an Action who shares a category with
    the former
    """
 
    #1 joined action reached a level step
    action = sender
    old_status = kwargs['old_status']

    log.debug("Action:%s status:%s" % (action, old_status)) 

    #Matteo switch status values (if READY --> ... else: TODO placeholder)

    if old_status == action_consts.ACTION_STATUS_READY: 

        extra_context = ({
            "action" : action,
            "old_status" : old_status
        }) 
        #recipients
        users = action.voters
        #print "\n\nRecipients: %s" % users

        notification.send(users=users,
            label="joined_action_get_level_step",
            extra_context=extra_context,
            on_site=True, 
            sender=None, 
            now=True
        )

        #2 favourite topic action reached a level step
    else:
        #TODO placeholder old_status other than READY
        pass

#@receiver(post_action_status_update, sender=Action)
@receiver(post_save, sender=ActionRequest)
def register_status_update_activity(sender, **kwargs):
    """ Create a new Activity if the status is 'victory' or 'closed' """
 
    if kwargs['created']:
        action_request = kwargs['instance']

        action = action_request.action
        user = action_request.sender
        question = action.question
        old_status = action.status

        if old_status in (action_consts.ACTION_STATUS_VICTORY,
            action_consts.ACTION_STATUS_CLOSED
        ):
            activity_type = [
                ae_consts.OA_TYPE_ACTIVITY_SET_CLOSURE, 
                ae_consts.OA_TYPE_ACTIVITY_SET_VICTORY
            ][old_status in (action_consts.ACTION_STATUS_VICTORY)]

            log.debug("ACTIVITY with Action:%s status:%s" % (action, old_status)) 

            activity = Activity(
                    user=user,
                    content_object=action,
                    activity_type=activity_type,
                    question=question
            )
            activity.save()


#NOTE: KO: the default settings should have been setted in the user pre_save
#@receiver(post_save, sender=User)
#def user_set_default_notice_backend(sender, **kwargs):
#    """ Indicates for the User whether to send notifications
#    of a given type to the openaction default medium. """
#
#    if kwargs['created']:
#        user = kwargs['instance']
#
#        if user.is_active:
#
#            for notice_type in notification.NoticeType.objects.all():
#                obj, created = notification.NoticeSetting.objects.get_or_create(
#                    user=user, 
#                    notice_type=notice_type, 
#                    medium="openaction", 
#                    send=True
#                )
#                log.debug("Adding NoticeSetting of type %s to user %s " % (
#                    notice_type, 
#                    user
#                ))

#handle the moderation requests from the action owner
@receiver(action_moderation_request_submitted, sender=ActionRequest)
def notify_action_moderation_request(sender, **kwargs):
    """ Notify to an action follower that he received a moderation
    request from the action owner"""

    action_request = sender

    #recipients
    if action_request.recipient:
        users = [action_request.recipient]
    else:
        # Send notification to staff users
        # OpenPolis/ActionAID people who manage the software
        users = User.objects.filter(is_staff=True)

    #extra_context
    extra_context = ({
        "action_request" : action_request,
        "process_url" : reverse("actionrequest-moderation-process", args=(action_request.pk,))
    }) 

    notification.send(users=users,
        label="mod_proposal",
        extra_context=extra_context,
        on_site=True, 
        sender=None, 
        now=True
    )

#handle the moderation processing of the questioned user
@receiver(action_moderation_request_processed, sender=ActionRequest)
def notify_action_moderation_processed(sender, **kwargs):
    """ Notify to the Action owner that an Action follower sent a response
    to an Action moderation request"""

    action_request = sender

    #recipients
    users = []
    users.append(action_request.action.owner)
    #extra_context
    extra_context = ({
        "action_request" : action_request,
    }) 

    notification.send(users=users,
        label="answer_mod_proposal",
        extra_context=extra_context,
        on_site=True, 
        sender=None, 
        now=True
    )
