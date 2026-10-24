// POST /api/checkout -> { clientSecret } for Stripe embedded Checkout.
// One fixed price, once, from ../offer.json. The buyer's password is minted here so it can ride
// in the invoice footer (Stripe's own invoice email is a second copy of it).
const { OFFER, SITE, PRODUCT, stripe, newPassword } = require("./_lib");

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });
  try {
    const { nonce, password } = newPassword();
    // Two things are sold here: the full table (OFFER) and the fixed-price contract (OFFER.contract,
    // sold from /contract/ and /contract/for/<token>/). Both mint a password, so a contract buyer
    // gets the full table on the day they pay; metadata.kind tells the emails apart.
    const contract = req.body && req.body.offer === "contract";
    const O = contract ? OFFER.contract : OFFER;
    // Back to the page they bought from: /, /for/<token>/, /contract/ or /contract/for/<token>/.
    const from = String((req.body && req.body.path) || "/");
    const back = /^\/((contract\/)?(for\/[a-z0-9]{6,16}\/?)?|contract)$/.test(from) ? from : contract ? "/contract/" : "/";
    const s = await stripe("checkout/sessions", {
      method: "POST",
      form: {
        ui_mode: "embedded_page",
        mode: "payment",
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][unit_amount]": String(O.price_usd * 100),
        "line_items[0][price_data][product_data][name]": O.name,
        "line_items[0][price_data][product_data][description]": O.description,
        "payment_method_types[0]": "card",
        "payment_method_types[1]": "link",
        customer_creation: "always",
        "invoice_creation[enabled]": "true",
        "invoice_creation[invoice_data][description]": O.name,
        "invoice_creation[invoice_data][custom_fields][0][name]": "Password",
        "invoice_creation[invoice_data][custom_fields][0][value]": password,
        "invoice_creation[invoice_data][custom_fields][1][name]": "Open at",
        "invoice_creation[invoice_data][custom_fields][1][value]": SITE.replace("https://", ""),
        "invoice_creation[invoice_data][footer]": `Your password: ${password}. Open the ${OFFER.thing} at ${SITE}/?pw=${password}. Brick & Mortar · hello@brickandmortar.dev`,
        "invoice_creation[invoice_data][metadata][product]": PRODUCT,
        "metadata[product]": PRODUCT,
        "metadata[kind]": contract ? "contract" : "table",
        ...(contract ? { "metadata[for]": String((from.match(/for\/([a-z0-9]{6,16})/) || [])[1] || "") } : {}),
        "metadata[pw_nonce]": nonce,
        "metadata[password]": password,
        "payment_intent_data[metadata][product]": PRODUCT,
        "payment_intent_data[metadata][pw_nonce]": nonce,
        "payment_intent_data[metadata][kind]": contract ? "contract" : "table",
        "payment_intent_data[description]": O.name,
        return_url: `${SITE}${back}?paid={CHECKOUT_SESSION_ID}`,
      },
    });
    res.status(200).json({ clientSecret: s.client_secret });
  } catch (e) {
    console.error("[checkout]", e.message);
    res.status(502).json({ error: "Checkout could not start. Please try again in a minute." });
  }
};
