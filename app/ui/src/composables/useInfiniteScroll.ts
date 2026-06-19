import { ref, onMounted, onUnmounted, type Ref } from 'vue'

export function useInfiniteScroll(
  loadMore: () => Promise<void>,
  hasMore: Ref<boolean>,
  loading: Ref<boolean>,
) {
  const sentinelRef = ref<HTMLElement | null>(null)
  let observer: IntersectionObserver | null = null

  onMounted(() => {
    observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && hasMore.value && !loading.value) {
          loadMore()
        }
      },
      { rootMargin: '200px' },
    )
    if (sentinelRef.value) observer.observe(sentinelRef.value)
  })

  onUnmounted(() => {
    observer?.disconnect()
  })

  return { sentinelRef }
}
