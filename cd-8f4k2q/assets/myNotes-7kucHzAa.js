import{c as o}from"./index-YuUpJbCl.js";/**
 * @license lucide-react v0.453.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const c=o("Check",[["path",{d:"M20 6 9 17l-5-5",key:"1gmf2c"}]]);/**
 * @license lucide-react v0.453.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const u=o("Pin",[["path",{d:"M12 17v5",key:"bb1du9"}],["path",{d:"M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z",key:"1nkz8b"}]]),i="wb_notes_v1";function d(e){return Array.isArray(e)?e.filter(n=>n&&typeof n.text=="string"):[]}function f(){try{return d(JSON.parse(localStorage.getItem(i)))}catch{return[]}}function l(e){try{localStorage.setItem(i,JSON.stringify(e))}catch{}return e}function r(){return`n${Date.now().toString(36)}${Math.random().toString(36).slice(2,6)}`}function g(e,n,t=""){const a=String(n||"").trim();return a?[{id:r(),text:a,due:String(t||"").slice(0,16),done:!1,pinned:!1,createdAt:new Date().toISOString()},...e]:e}function p(e,n){return e.map(t=>t.id===n?{...t,done:!t.done}:t)}function S(e,n){return e.map(t=>t.id===n?{...t,pinned:!t.pinned}:t)}function A(e,n){return e.filter(t=>t.id!==n)}function m(e){return e.filter(n=>!n.done)}function y(e){const n=Array.isArray(e)?e:[];return[...n.filter(t=>t.pinned&&!t.done),...n.filter(t=>!t.pinned||t.done)]}function N(){return[{id:`${r()}a`,text:"PHY 1201 Written Assignment 1 别忘了交",due:"",done:!1,pinned:!0,createdAt:new Date().toISOString()},{id:`${r()}b`,text:"周日 PHY 1201 补课（AC5-318）",due:"2026-09-20T08:30",done:!1,pinned:!1,createdAt:new Date().toISOString()},{id:`${r()}c`,text:"买便签纸",due:"",done:!0,pinned:!1,createdAt:new Date().toISOString()}]}export{c as C,u as P,N as a,y as b,p as c,m as d,g as e,f as l,A as r,l as s,S as t};
