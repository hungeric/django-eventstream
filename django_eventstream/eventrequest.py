import urllib
from .utils import parse_grip_last, parse_last_event_id

class EventRequest(object):
	class Error(ValueError):
		pass

	class GripError(Error):
		pass

	class ResumeNotAllowedError(Error):
		pass

	def __init__(self, http_request=None, channel_limit=10):
		self.channels = set()
		self.channel_last_ids = {}
		self.is_recover = False

		if http_request:
			self.apply_http_request(http_request,
				channel_limit=channel_limit)

	def apply_http_request(self, http_request, channel_limit):
		channels = set(http_request.GET.getlist('channel'))
		is_recover = False

		if len(channels) < 1:
			raise EventRequest.Error('No channels specified')

		if len(channels) > channel_limit:
			raise EventRequest.Error('Channel limit exceeded')

		grip_last = http_request.META.get('HTTP_GRIP_LAST')
		if grip_last:
			try:
				grip_last = parse_grip_last(grip_last)
			except:
				raise EventRequest.GripError(
					'Failed to parse Grip-Last header')

			channel_last_ids = {}
			is_recover = True
			for grip_channel, last_id in grip_last.iteritems():
				if not grip_channel.startswith('events-'):
					continue
				channel = urllib.unquote(grip_channel[7:])
				if channel in channels:
					channel_last_ids[channel] = last_id
		else:
			last_event_id = http_request.META.get('HTTP_LAST_EVENT_ID')
			if not last_event_id:
				# take the first non-empty param, from the end
				for val in reversed(http_request.GET.getlist('lastEventId')):
					if val:
						last_event_id = val
						break

			if last_event_id:
				if last_event_id == 'error':
					raise EventRequest.ResumeNotAllowedError(
						'Can\'t resume session after stream-error')

				try:
					parsed = parse_last_event_id(last_event_id)

					channel_last_ids = {}
					for channel, last_id in parsed.iteritems():
						channel = urllib.unquote(channel)
						if channel in channels:
							channel_last_ids[channel] = last_id
				except:
					raise EventRequest.Error(
						'Failed to parse Last-Event-ID or lastEventId')
			else:
				channel_last_ids = {}
				for channel in channels:
					channel_last_ids[channel] = None

		self.channels = set(channel_last_ids.keys())
		self.channel_last_ids = channel_last_ids
		self.is_recover = is_recover