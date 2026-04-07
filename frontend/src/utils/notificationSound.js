let audioContext = null

function getAudioContext() {
  if (typeof window === 'undefined') return null
  const AudioContextClass = window.AudioContext || window.webkitAudioContext
  if (!AudioContextClass) return null
  if (!audioContext) {
    audioContext = new AudioContextClass()
  }
  return audioContext
}

export async function playNotificationSound() {
  if (typeof document !== 'undefined' && document.visibilityState !== 'visible') {
    return
  }

  if (typeof window !== 'undefined' && typeof window.hasFocus === 'function' && !window.hasFocus()) {
    return
  }

  const context = getAudioContext()
  if (!context) return

  try {
    if (context.state === 'suspended') {
      await context.resume()
    }

    const now = context.currentTime
    const oscillator = context.createOscillator()
    const gain = context.createGain()

    oscillator.type = 'sine'
    oscillator.frequency.setValueAtTime(740, now)
    oscillator.frequency.exponentialRampToValueAtTime(880, now + 0.12)

    gain.gain.setValueAtTime(0.0001, now)
    gain.gain.exponentialRampToValueAtTime(0.08, now + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.22)

    oscillator.connect(gain)
    gain.connect(context.destination)

    oscillator.start(now)
    oscillator.stop(now + 0.24)
  } catch (error) {
    // Ignore autoplay/browser audio restrictions and fail silently.
  }
}
