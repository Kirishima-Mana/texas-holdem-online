const actionAudioMap: Record<string, string> = {
  bet: '/Audio/bet.mp3',
  call: '/Audio/call.mp3',
  raise: '/Audio/raise.mp3',
  check: '/Audio/check.mp3',
  fold: '/Audio/fold.mp3',
  all_in: '/Audio/all in.mp3',
}

export function playActionSound(action: string): void {
  const audioPath = actionAudioMap[action]
  if (!audioPath) return
  const audio = new Audio(audioPath)
  audio.play().catch(() => {
    // 浏览器自动播放策略可能阻止，忽略
  })
}
