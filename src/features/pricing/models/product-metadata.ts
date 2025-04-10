import z from 'zod';

export const priceCardVariantSchema = z.enum(['basic', 'pro', 'enterprise']);

export const productMetadataSchema = z
  .object({
    price_card_variant: priceCardVariantSchema,
    // 後方互換性のために両方のフィールドをオプショナルにする
    generated_articles: z.string().optional(),
    generated_images: z.string().optional(),
    article_length: z.string().optional(),
    image_editor: z.enum(['basic', 'pro']).optional(),
    seo_optimization: z.string().optional(),
    chat_edits: z.string().optional(),
    export_formats: z.string().optional(),
    api_access: z.string().optional(),
    custom_branding: z.string().optional(),
    support_level: z.enum(['email', 'live', '専任担当者']).optional(),
  })
  .transform((data) => {
    // generatedArticles は generated_articles または generated_images から取得
    const generatedArticles = data.generated_articles 
      ? (isNaN(parseInt(data.generated_articles)) ? data.generated_articles : parseInt(data.generated_articles))
      : (data.generated_images ? (isNaN(parseInt(data.generated_images)) ? data.generated_images : parseInt(data.generated_images)) : 0);
    
    return {
      priceCardVariant: data.price_card_variant,
      generatedArticles,
      articleLength: data.article_length,
      imageEditor: data.image_editor,
      seoOptimization: data.seo_optimization,
      chatEdits: data.chat_edits,
      exportFormats: data.export_formats,
      apiAccess: data.api_access,
      customBranding: data.custom_branding,
      supportLevel: data.support_level || 'email',
    };
  });

export type ProductMetadata = z.infer<typeof productMetadataSchema>;
export type PriceCardVariant = z.infer<typeof priceCardVariantSchema>;
