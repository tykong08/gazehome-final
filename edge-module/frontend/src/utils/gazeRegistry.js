const registry = new Map()

/**
 * Register a DOM element to receive gaze enter/leave callbacks.
 * Returns a cleanup function that must be called when the element unmounts.
 */
export function registerGazeTarget(element, handlers) {
    if (!element) return () => {}

    registry.set(element, handlers)

    return () => {
        const stored = registry.get(element)
        if (stored === handlers) {
            registry.delete(element)
        }
    }
}

/**
 * Walk up the DOM tree to find the nearest registered gaze target for the node.
 */
export function resolveGazeTarget(node) {
    let current = node
    while (current) {
        if (registry.has(current)) {
            return {
                element: current,
                handlers: registry.get(current)
            }
        }
        current = current.parentElement
    }
    return null
}

/**
 * Utility for tests/debugging to clear all registrations.
 */
export function __clearGazeRegistry() {
    registry.clear()
}

