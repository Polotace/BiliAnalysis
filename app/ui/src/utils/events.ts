import mitt from 'mitt'

type Events = {
  'auth:logout': void
  'app:refresh': void
}

export const bus = mitt<Events>()
