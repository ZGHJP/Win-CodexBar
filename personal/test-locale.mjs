// Test-process-only locale parity. Production and the user's settings are untouched.
const defaultLocale = (locale) => locale == null || (Array.isArray(locale) && !locale.length) ? "en-US" : locale;
for (const name of ["NumberFormat", "DateTimeFormat"]) {
  const Native = Intl[name];
  Intl[name] = new Proxy(Native, {
    construct(target, args, receiver) { return Reflect.construct(target, [defaultLocale(args[0]), ...args.slice(1)], receiver); },
    apply(target, receiver, args) { return Reflect.apply(target, receiver, [defaultLocale(args[0]), ...args.slice(1)]); },
  });
}
for (const name of ["toLocaleString", "toLocaleDateString", "toLocaleTimeString"]) {
  const native = Date.prototype[name];
  Date.prototype[name] = function(locale, ...rest) { return Reflect.apply(native, this, [defaultLocale(locale), ...rest]); };
}
