# HoodooMart UI

Vietnamese product discovery, primarily fashion in the current original fixture. Preserve the M0 navy/blue palette: ink #20313E, navy #203E59, action #2479A8, pale blue #EFF6FA, white #FFFFFF, muted #627582. Local system sans with Vietnamese coverage; no font network dependency.

One memorable area: a wide search workbench that gives text, voice and image equal discoverability. Quiet navigation, generous product imagery, visible applied conditions and price. No invented promotions/reviews/counters. Product attributes and taxonomy fetched from the API. Original illustrations and simulated data are labelled.

Desktop: compact masthead, search panel, category navigation, 4-column product grid and filter sidebar. Mobile: visible cart/account links, full-width search, disclosure filters and 2-column grid at 360px. Controls ≥44px, visible focus, reduced-motion support, semantic headings/landmarks, Vietnamese error paths with retry.

Use shadcn primitives for buttons, fields, alerts, badges, dialogs/sheets and skeletons; semantic theme tokens. Server components render product name/price/stock and GET search URLs. Small client components own recording, preview, suggestions, guest cart and authenticated actions. VND is integer and formatted by Intl vi-VN.
