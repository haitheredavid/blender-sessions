/** One record of public/models.json, written by `blend site`. */
export type ModelEntry = {
  name: string;
  title: string;
  created: string;
  intent: string;
  tags: string[];
  status: string;
  upright: boolean;
  model: string;
  parts: string | null;
  render: string | null;
  brief: string;
  speckle: string | null;
};

/** Site-relative path -> URL under the deploy base. */
export const asset = (path: string) => `${import.meta.env.BASE_URL}${path}`;
