import { jwtVerify, SignJWT } from 'jose';

const getMfaSecret = () => {
  const secret =
    process.env.ADMIN_MFA_SESSION_SECRET ||
    'dev-mfa-secret-change-in-production';
  return new TextEncoder().encode(secret);
};

export async function createMfaSessionToken(userId: string): Promise<string> {
  const ttlHours = parseInt(
    process.env.ADMIN_MFA_SESSION_TTL_HOURS || '8',
    10
  );
  return new SignJWT({ sub: userId })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime(`${ttlHours}h`)
    .sign(getMfaSecret());
}

export async function verifyMfaSessionToken(
  token: string,
  expectedUserId: string
): Promise<boolean> {
  try {
    const { payload } = await jwtVerify(token, getMfaSecret());
    return payload.sub === expectedUserId;
  } catch {
    return false;
  }
}

export function getMfaCookieOptions() {
  const isProduction = process.env.NODE_ENV === 'production';
  const ttlHours = parseInt(
    process.env.ADMIN_MFA_SESSION_TTL_HOURS || '8',
    10
  );
  return {
    httpOnly: true,
    secure: isProduction,
    sameSite: 'strict' as const,
    path: '/',
    maxAge: ttlHours * 60 * 60,
  };
}
